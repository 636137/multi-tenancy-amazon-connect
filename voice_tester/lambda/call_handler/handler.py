"""
Call Handler Lambda

Handles Amazon Chime SDK SIP Media Application (PSMA) events.
This is the entry point for all PSTN calls made by the testing system.

Event Flow:
1. NEW_INBOUND_CALL / NEW_OUTBOUND_CALL - Call initiated
2. RINGING - Target phone ringing
3. CALL_ANSWERED - Call connected
4. ACTION_SUCCESSFUL / ACTION_FAILED - Action results
5. HANGUP - Call ended
"""

import base64
import io
import json
import logging
import os
import random
import re
import time
import uuid
import wave
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import boto3

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'INFO')
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

# AWS clients
_dynamodb = boto3.resource('dynamodb')
_s3 = boto3.client('s3')
_lambda = boto3.client('lambda')
_bedrock = boto3.client('bedrock-runtime')

# Environment
CALL_STATE_TABLE = os.environ.get('CALL_STATE_TABLE', 'VoiceTestCallState')
TEST_RESULTS_TABLE = os.environ.get('TEST_RESULTS_TABLE', 'VoiceTestResults')
RECORDINGS_BUCKET = os.environ.get('RECORDINGS_BUCKET', '')

# Optional overrides
NOVA_SONIC_PROCESSOR = (
    os.environ.get('NOVA_SONIC_PROCESSOR_ARN')
    or os.environ.get('NOVA_SONIC_PROCESSOR_NAME')
    or 'VoiceTest-NovaSonicProcessor'
)
AUDIO_PROCESSOR = (
    os.environ.get('AUDIO_PROCESSOR_ARN')
    or os.environ.get('AUDIO_PROCESSOR_NAME')
    or 'VoiceTest-AudioProcessor'
)
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')

# Tuning
DEFAULT_LISTEN_SNIPPET_SECONDS = int(os.environ.get('LISTEN_SNIPPET_SECONDS', '6'))


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    logger.info(f"Received event: {json.dumps(event)}")

    invoke_event = event.get('InvocationEventType', '')
    call_details = event.get('CallDetails', {}) or {}
    transaction_id = call_details.get('TransactionId', '')

    # Use TransactionId as the stable key for call state.
    state_call_id = transaction_id

    logger.info(f"Event: {invoke_event}, CallId: {state_call_id}")

    try:
        if invoke_event == 'NEW_OUTBOUND_CALL':
            return handle_new_outbound_call(event, state_call_id, transaction_id)
        if invoke_event == 'RINGING':
            return handle_ringing(event, state_call_id)
        if invoke_event == 'CALL_ANSWERED':
            return handle_call_answered(event, state_call_id)
        if invoke_event == 'ACTION_SUCCESSFUL':
            return handle_action_successful(event, state_call_id)
        if invoke_event == 'ACTION_FAILED':
            return handle_action_failed(event, state_call_id)
        if invoke_event == 'HANGUP':
            return handle_hangup(event, state_call_id)
        if invoke_event == 'CALL_UPDATE_REQUESTED':
            return handle_call_update(event, state_call_id)

        logger.warning(f"Unhandled event type: {invoke_event}")
        return create_response([])

    except Exception as e:
        logger.error(f"Error handling event: {str(e)}", exc_info=True)
        return create_response([{ "Type": "Hangup", "Parameters": {"SipResponseCode": "500"}}])


def create_response(actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"SchemaVersion": "1.0", "Actions": actions}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json_loads(s: Optional[str]) -> Optional[Dict[str, Any]]:
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def _extract_participant_call_id(event: Dict[str, Any]) -> str:
    call_details = event.get('CallDetails', {}) or {}
    participants = call_details.get('Participants', []) or []
    return next((p.get('CallId') for p in participants if p.get('CallId')), '')


def _get_step_index_by_id(steps: List[Dict[str, Any]], step_id: str) -> Optional[int]:
    for i, s in enumerate(steps):
        if s.get('id') == step_id:
            return i
    return None


def _advance_to_next(call_id: str, call_state: Dict[str, Any], *, next_step_id: Optional[str] = None) -> None:
    scenario = call_state.get('scenario_data', {}) or {}
    steps = scenario.get('steps', []) or []
    cur = int(call_state.get('current_step_index', 0) or 0)

    idx: Optional[int] = None
    if next_step_id:
        idx = _get_step_index_by_id(steps, next_step_id)

    if idx is None:
        idx = cur + 1

    update_call_state(call_id, {
        'current_step_index': int(idx),
        'current_step_id': (steps[idx].get('id') if 0 <= idx < len(steps) else None),
    })


def _set_step_outcome(call_id: str, step_id: str, outcome: Dict[str, Any]) -> None:
    # Store a compact per-step outcome for success_criteria evaluation.
    call_state = get_call_state(call_id) or {}
    outcomes = call_state.get('step_outcomes', {}) or {}
    outcomes[step_id] = outcome
    update_call_state(call_id, {'step_outcomes': outcomes})


def _match_patterns(text: str, patterns: List[str]) -> List[str]:
    matched: List[str] = []
    for p in patterns or []:
        if not p:
            continue
        try:
            if re.search(p, text or '', re.IGNORECASE):
                matched.append(p)
        except re.error:
            if p.lower() in (text or '').lower():
                matched.append(p)
    return matched


def _wav_to_pcm(wav_bytes: bytes) -> Tuple[bytes, int]:
    """Return (pcm_s16le_mono_bytes, sample_rate)."""
    with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
        nchan = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        fr = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    # We expect 16-bit PCM. If stereo, take left channel.
    if sampwidth != 2:
        # Best-effort: pass through bytes and hope Nova handles it.
        return frames, fr

    if nchan == 1:
        return frames, fr

    # Downmix by selecting first channel.
    # frames is interleaved little-endian 16-bit.
    out = bytearray()
    step = 2 * nchan
    for i in range(0, len(frames), step):
        out.extend(frames[i:i+2])
    return bytes(out), fr


def _invoke_lambda_json(function_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    resp = _lambda.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload).encode('utf-8'),
    )
    raw = resp['Payload'].read()
    try:
        return json.loads(raw)
    except Exception:
        try:
            return json.loads(raw.decode('utf-8'))
        except Exception:
            return {'statusCode': 500, 'error': 'invalid_lambda_response'}


def _start_transcribe_job_for_s3_wav(*, bucket: str, key: str, sample_rate: int = 8000) -> str:
    result = _invoke_lambda_json(
        AUDIO_PROCESSOR,
        {
            'operation': 'transcribe_s3',
            'bucket': bucket,
            'key': key,
            'media_format': 'wav',
            'sample_rate': int(sample_rate),
        },
    )
    if (result or {}).get('statusCode') != 202:
        raise RuntimeError((result or {}).get('error', 'transcribe_start_failed'))
    return (result.get('job_name') or '').strip()


def _poll_transcribe_job(job_name: str) -> Dict[str, Any]:
    result = _invoke_lambda_json(
        AUDIO_PROCESSOR,
        {
            'operation': 'transcribe_s3',
            'job_name': job_name,
        },
    )
    if (result or {}).get('statusCode') != 200:
        raise RuntimeError((result or {}).get('error', 'transcribe_poll_failed'))
    return result


def _generate_text_via_bedrock(*, system_prompt: str, user_prompt: str, max_tokens: int = 180) -> str:
    body = {
        'anthropic_version': 'bedrock-2023-05-31',
        'max_tokens': max_tokens,
        'temperature': 0.7,
        'system': system_prompt,
        'messages': [
            {'role': 'user', 'content': user_prompt},
        ],
    }
    resp = _bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType='application/json',
        accept='application/json',
        body=json.dumps(body),
    )
    out = json.loads(resp['body'].read())
    text = (out.get('content') or [{}])[0].get('text', '').strip()

    # Clean common artifacts
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()
    if text.startswith("'") and text.endswith("'"):
        text = text[1:-1].strip()

    for prefix in ['YOU:', 'Caller:', 'Response:', '[Caller]:', '[Response]:', 'CALLER:']:
        if text.upper().startswith(prefix.upper()):
            text = text[len(prefix):].strip()

    # Keep it short-ish for telephony
    return text[:500]


def _scenario_persona_prompt(scenario: Dict[str, Any]) -> str:
    persona = scenario.get('persona', {}) or {}
    sys_prompt = (persona.get('system_prompt') or '').strip()
    background = (persona.get('background') or '').strip()
    name = persona.get('name') or 'Caller'

    parts: List[str] = [
        f"You are the phone caller in an automated regression test. Persona name: {name}.",
    ]

    if sys_prompt:
        parts.append("Persona instructions:\n" + sys_prompt)
    elif background:
        parts.append("Background:\n" + background)

    parts.append(
        "Rules: Reply with ONLY the exact words to speak. No narration, no quotes. Keep it brief (1-2 sentences)."
    )

    return "\n\n".join(parts)


def handle_new_outbound_call(event: Dict[str, Any], call_id: str, transaction_id: str) -> Dict[str, Any]:
    # NEW_OUTBOUND_CALL can arrive before the TestRunner has finished persisting scenario_data.
    # Be careful to not clobber existing state, and avoid generating a random test_id (it must match the runner).
    logger.info(f"New outbound call: {call_id}")

    call_details = event.get('CallDetails', {}) or {}
    sma_call = call_details.get('SipMediaApplicationCall', {}) or {}

    sip_headers = (call_details.get('SipHeaders') or sma_call.get('SipHeaders') or {}) or {}
    sip_headers_lc = {str(k).lower(): v for k, v in (sip_headers or {}).items()}

    # Chime events may use different field names for the arguments map, and may nest it under SipMediaApplicationCall.
    raw_args = (
        call_details.get('Arguments')
        or call_details.get('ArgumentsMap')
        or sma_call.get('Arguments')
        or sma_call.get('ArgumentsMap')
        or {}
    ) or {}
    arguments = raw_args if isinstance(raw_args, dict) else {}
    arguments_lc = {str(k).lower(): v for k, v in (arguments or {}).items()}

    # Extract test/scenario identifiers case-insensitively.
    arg_test_id = arguments.get('test_id') or arguments_lc.get('test_id')
    hdr_test_id = sip_headers.get('X-Test-Id') or sip_headers_lc.get('x-test-id')
    event_test_id = (arg_test_id or hdr_test_id or '').strip() if isinstance((arg_test_id or hdr_test_id), str) else (arg_test_id or hdr_test_id)

    arg_results_ts = arguments.get('results_timestamp') or arguments_lc.get('results_timestamp')
    hdr_results_ts = sip_headers.get('X-Test-Timestamp') or sip_headers_lc.get('x-test-timestamp')
    event_results_ts = (arg_results_ts or hdr_results_ts or '').strip() if isinstance((arg_results_ts or hdr_results_ts), str) else (arg_results_ts or hdr_results_ts)

    arg_scenario_json = arguments.get('scenario') or arguments_lc.get('scenario')
    hdr_scenario_name = sip_headers.get('X-Scenario') or sip_headers_lc.get('x-scenario')

    # Some SMA events don't surface SipHeaders/Arguments; fall back to looking up the originating test by TransactionId.
    scanned_test_id = None
    scanned_scenario_name = None
    scanned_results_ts = None
    if (not event_test_id or not event_results_ts) and transaction_id:
        try:
            from boto3.dynamodb.conditions import Attr

            results_table = _dynamodb.Table(TEST_RESULTS_TABLE)
            scan = results_table.scan(
                FilterExpression=Attr('transaction_id').eq(transaction_id),
                ProjectionExpression='test_id, scenario_name, #ts',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                Limit=1,
            )
            items = scan.get('Items', []) or []
            if items:
                scanned_test_id = items[0].get('test_id')
                scanned_scenario_name = items[0].get('scenario_name')
                scanned_results_ts = items[0].get('timestamp')
        except Exception as e:
            logger.warning(f"Unable to scan VoiceTestResults for transaction_id {transaction_id}: {e}")

    if scanned_test_id and not event_test_id:
        event_test_id = scanned_test_id
    if scanned_results_ts and not event_results_ts:
        event_results_ts = scanned_results_ts
    if scanned_scenario_name and not hdr_scenario_name:
        hdr_scenario_name = scanned_scenario_name

    # Load any existing state (might have been created by the TestRunner).
    existing = get_call_state(call_id) or {}

    now_iso = _utcnow_iso()
    now_ttl = int(datetime.now(timezone.utc).timestamp()) + 3600

    parsed_scenario = None
    if arg_scenario_json and 'scenario_data' not in existing:
        # DynamoDB does not accept float types; parse floats as Decimal.
        from decimal import Decimal
        try:
            if isinstance(arg_scenario_json, str):
                parsed_scenario = json.loads(arg_scenario_json, parse_float=Decimal)
            elif isinstance(arg_scenario_json, dict):
                parsed_scenario = json.loads(json.dumps(arg_scenario_json), parse_float=Decimal)
        except Exception:
            parsed_scenario = None

    updates: Dict[str, Any] = {
        'transaction_id': transaction_id,
        'status': 'INITIATING',
    }
    if event_results_ts:
        updates['results_timestamp'] = event_results_ts

    # Only initialize defaults if this is the first writer.
    if not existing:
        updates.update({
            'started_at': now_iso,
            'conversation': [],
            'current_step_index': 0,
            'step_outcomes': {},
            'ttl': now_ttl,
        })

    # Prefer the event-supplied test_id (should match the TestRunner's test_id). If missing, fall back to call_id.
    updates['test_id'] = event_test_id or existing.get('test_id') or call_id

    # Scenario name: use parsed scenario name, header/scan, then existing/scenario_data.
    existing_scenario_name = existing.get('scenario_name')
    if not existing_scenario_name and isinstance(existing.get('scenario_data'), dict):
        existing_scenario_name = (existing.get('scenario_data') or {}).get('name')

    scenario_name = (parsed_scenario or {}).get('name') or hdr_scenario_name or existing_scenario_name or 'unknown'
    updates['scenario_name'] = scenario_name

    # Only set scenario_data if we don't already have it.
    if parsed_scenario and 'scenario_data' not in existing:
        updates['scenario_data'] = parsed_scenario

    update_call_state(call_id, updates)
    return create_response([])


def handle_ringing(event: Dict[str, Any], call_id: str) -> Dict[str, Any]:
    logger.info(f"Call ringing: {call_id}")
    update_call_state(call_id, {'status': 'RINGING'})
    return create_response([])


def handle_call_answered(event: Dict[str, Any], call_id: str) -> Dict[str, Any]:
    logger.info(f"Call answered: {call_id}")

    participant_call_id = _extract_participant_call_id(event)

    update_call_state(call_id, {
        'status': 'IN_PROGRESS',
        'answered_at': _utcnow_iso(),
        'participant_call_id': participant_call_id,
    })

    call_state = get_call_state(call_id) or {}

    actions: List[Dict[str, Any]] = []

    # Only record when explicitly enabled in the scenario.
    recording_cfg = ((call_state.get('scenario_data') or {}).get('target', {}) or {}).get('recording', {}) or {}
    recording_enabled = bool(recording_cfg.get('enabled', False))

    if RECORDINGS_BUCKET and recording_enabled and participant_call_id:
        test_id = call_state.get('test_id', call_id)
        actions.append({
            'Type': 'StartCallRecording',
            'Parameters': {
                'CallId': participant_call_id,
                'Track': 'BOTH',
                'Destination': {
                    'Type': 'S3',
                    'Location': f"{RECORDINGS_BUCKET}/recordings/{test_id}",
                },
            },
        })

    # Give the far end a moment to start talking.
    actions.append({'Type': 'Pause', 'Parameters': {'DurationInMilliseconds': 800}})

    return {
        'SchemaVersion': '1.0',
        'Actions': actions,
        'TransactionAttributes': {
            'testId': call_state.get('test_id', ''),
            'callId': call_id,
        },
    }


def handle_action_successful(event: Dict[str, Any], call_id: str) -> Dict[str, Any]:
    action_data = event.get('ActionData', {}) or {}
    action_type = action_data.get('Type', '')
    logger.info(f"Action successful: {action_type} for call {call_id}")

    call_state = get_call_state(call_id)
    if not call_state:
        logger.error(f"No call state found for {call_id}")
        return create_response([{'Type': 'Hangup'}])

    # Refresh participant call id if available
    participant_call_id = _extract_participant_call_id(event)
    if participant_call_id and participant_call_id != call_state.get('participant_call_id'):
        update_call_state(call_id, {'participant_call_id': participant_call_id})
        call_state['participant_call_id'] = participant_call_id

    if action_type == 'StartCallRecording':
        update_call_state(call_id, {'recording_started': True})
        return create_response([])

    if action_type == 'Speak':
        # After speaking, pause briefly then continue
        return create_response([{'Type': 'Pause', 'Parameters': {'DurationInMilliseconds': 500}}])

    if action_type == 'SendDigits':
        return create_response([{'Type': 'Pause', 'Parameters': {'DurationInMilliseconds': 500}}])

    if action_type == 'Pause':
        return generate_next_action(call_id, call_state)

    if action_type == 'RecordAudio':
        return handle_record_audio_success(call_id, call_state, action_data)

    return create_response([])


def handle_action_failed(event: Dict[str, Any], call_id: str) -> Dict[str, Any]:
    action_data = event.get('ActionData', {}) or {}
    action_type = action_data.get('Type', '')
    error = (
        action_data.get('Error')
        or action_data.get('ErrorMessage')
        or action_data.get('ErrorType')
        or 'Unknown error'
    )

    # Persist enough detail to diagnose SMA action failures.
    details = json.dumps(action_data, default=str)
    if len(details) > 1000:
        details = details[:1000] + '…'

    logger.error(f"Action failed: {action_type} - {error} for call {call_id}. ActionData={details}")
    add_to_conversation(call_id, 'error', f"Action {action_type} failed: {error}. ActionData={details}")
    update_call_state(call_id, {'status': 'FAILED', 'error': f"{action_type}: {error}", 'ended_at': _utcnow_iso()})

    return create_response([{'Type': 'Hangup', 'Parameters': {'SipResponseCode': '500'}}])


def handle_hangup(event: Dict[str, Any], call_id: str) -> Dict[str, Any]:
    logger.info(f"Call hangup: {call_id}")

    call_state = get_call_state(call_id)
    if not call_state:
        return create_response([])

    scenario = call_state.get('scenario_data', {}) or {}
    evaluation = evaluate_success_criteria(scenario, call_state)
    passed = evaluation.get('passed', False)
    final_status = 'COMPLETED' if passed else 'FAILED'

    update_call_state(call_id, {
        'status': final_status,
        'evaluation': evaluation,
        'ended_at': _utcnow_iso(),
    })

    final_state = get_call_state(call_id) or call_state
    save_test_results(final_state)

    return create_response([])


def handle_call_update(event: Dict[str, Any], call_id: str) -> Dict[str, Any]:
    logger.info(f"Call update requested: {call_id}")

    action_data = event.get('ActionData', {}) or {}
    requested_action = action_data.get('RequestedAction', '')

    if requested_action == 'Speak':
        text = action_data.get('Text', '')
        call_state = get_call_state(call_id) or {}
        participant_call_id = call_state.get('participant_call_id', '')
        if text and participant_call_id:
            return create_response([
                {
                    'Type': 'Speak',
                    'Parameters': {
                        'Text': text,
                        'CallId': participant_call_id,
                        'Engine': 'neural',
                        'LanguageCode': 'en-US',
                        'VoiceId': 'Joanna',
                    },
                }
            ])

    return create_response([])


def _continue_pending_transcription(call_id: str, call_state: Dict[str, Any]) -> Dict[str, Any]:
    pending = call_state.get('pending_transcription', {}) or {}
    job_name = pending.get('job_name')
    purpose = pending.get('purpose')
    step_id = pending.get('step_id')

    if not job_name:
        update_call_state(call_id, {'pending_transcription': None})
        return generate_next_action(call_id, get_call_state(call_id) or call_state)

    deadline_epoch = pending.get('deadline_epoch')
    if deadline_epoch is not None:
        try:
            if time.time() >= float(deadline_epoch):
                update_call_state(call_id, {'pending_transcription': None})
                # Re-enter the step loop (listen will timeout naturally if deadline passed)
                return generate_next_action(call_id, get_call_state(call_id) or call_state)
        except Exception:
            pass

    try:
        status_resp = _poll_transcribe_job(str(job_name))
    except Exception as e:
        add_to_conversation(call_id, 'error', f"transcribe_poll_failed: {e}", step_id=step_id, action=purpose)
        update_call_state(call_id, {'pending_transcription': None})
        return generate_next_action(call_id, get_call_state(call_id) or call_state)

    status = (status_resp.get('status') or '').upper()
    if status in ('QUEUED', 'IN_PROGRESS'):
        return create_response([{'Type': 'Pause', 'Parameters': {'DurationInMilliseconds': 500}}])

    transcript = (status_resp.get('transcript') or '').strip() if status == 'COMPLETED' else ''
    if status == 'FAILED':
        reason = status_resp.get('failure_reason', '')
        add_to_conversation(call_id, 'warn', f"transcribe_failed: {reason}", step_id=step_id, action=purpose)

    # Clear pending before applying transcript/advancing steps
    update_call_state(call_id, {'pending_transcription': None})

    call_state = get_call_state(call_id) or call_state

    if transcript:
        add_to_conversation(call_id, 'system', transcript, step_id=step_id, action=purpose)

    scenario = call_state.get('scenario_data', {}) or {}
    steps = scenario.get('steps', []) or []
    idx = _get_step_index_by_id(steps, step_id) if step_id else None

    if purpose == 'listen':
        expect_patterns = pending.get('expected_patterns', []) or []
        matched = _match_patterns(transcript, expect_patterns)

        if matched:
            _set_step_outcome(call_id, step_id, {
                'status': 'matched',
                'action': 'listen',
                'matched_patterns': matched,
                'expected_patterns': expect_patterns,
                'transcript': transcript,
            })

            next_step = None
            if idx is not None:
                step = steps[idx]
                next_step = step.get('on_match') or step.get('on_success') or step.get('next')

            _advance_to_next(call_id, call_state, next_step_id=next_step)
            update_call_state(call_id, {'listen_state': None})
            return generate_next_action(call_id, get_call_state(call_id) or call_state)

        # No match yet: continue listening
        if idx is not None:
            return start_or_continue_listen(call_id, call_state, steps[idx])
        return create_response([{'Type': 'Pause', 'Parameters': {'DurationInMilliseconds': 500}}])

    if purpose == 'agent':
        cfg_goal = (pending.get('goal') or '').strip()
        success_patterns = pending.get('success_patterns', []) or []
        end_patterns = pending.get('end_on_patterns', []) or []

        agent_state = (call_state.get('agent_state') or {}) or {}
        # If we see explicit end patterns, we can stop after at least one turn.
        end_matched = _match_patterns(transcript, end_patterns)
        success_matched = _match_patterns(transcript, success_patterns)

        if success_matched:
            _set_step_outcome(call_id, step_id, {
                'status': 'completed',
                'action': 'agent',
                'matched_patterns': success_matched,
                'transcript': transcript,
            })
            _advance_to_next(call_id, call_state, next_step_id=pending.get('next_step_id'))
            update_call_state(call_id, {'agent_state': None})
            return generate_next_action(call_id, get_call_state(call_id) or call_state)

        if end_matched and int(agent_state.get('turn', 0) or 0) > 0:
            # If the IVR is trying to wrap up (e.g., "anything else"), respond like a real caller
            # instead of silently ending the step.
            closing_text = "No thank you."
            add_to_conversation(call_id, 'caller', closing_text, step_id=step_id, action='agent')

            _set_step_outcome(call_id, step_id, {
                'status': 'completed',
                'action': 'agent',
                'ended_on_pattern': True,
                'matched_patterns': end_matched,
                'transcript': transcript,
            })
            _advance_to_next(call_id, call_state, next_step_id=pending.get('next_step_id'))
            update_call_state(call_id, {'agent_state': None})

            participant_call_id = call_state.get('participant_call_id', '')
            return create_response([
                {
                    'Type': 'Speak',
                    'Parameters': {
                        'Text': closing_text,
                        'CallId': participant_call_id,
                        'Engine': 'neural',
                        'LanguageCode': 'en-US',
                        'VoiceId': 'Joanna',
                    },
                }
            ])

        # Deterministic menu parsing: "press 1 for IRS" → {'1': 'IRS', ...}
        options: Dict[str, str] = {}
        for m in re.finditer(r"press\s+(\d)\s+for\s+([^\.,;]+)", transcript or '', re.IGNORECASE):
            options[m.group(1)] = m.group(2).strip()

        decision = None

        tr_lc = (transcript or '').lower()
        goal_first_line = (cfg_goal.splitlines()[0].strip() if cfg_goal else '')

        def _goal_to_utterance(line: str) -> str:
            line = (line or '').strip().rstrip('.')
            if not line:
                return "I'd like to check my refund status."
            if line.lower().startswith('check '):
                rest = line[0].lower() + line[1:]
                return f"I'd like to {rest}."
            return (line if line.endswith('.') else (line + '.'))

        # Heuristic fallbacks (work even if Bedrock isn't available)
        if cfg_goal and not decision:
            if re.search(r"after the tone|how can i help|what can i help|please (say|tell|speak)|state your question", tr_lc):
                decision = {'action': 'speak', 'text': _goal_to_utterance(goal_first_line)}
            elif re.search(r"social security|ssn", tr_lc):
                decision = {'action': 'speak', 'text': "I can provide the last four digits only."}
            elif re.search(r"filing status", tr_lc):
                decision = {'action': 'speak', 'text': "Single."}

        # DTMF selection from parsed options
        if options and cfg_goal and not decision:
            sys_prompt = _scenario_persona_prompt(scenario)
            opt_lines = "\n".join([f"{k}: {v}" for k, v in options.items()])
            user_prompt = f"""You are driving a phone IVR test.
GOAL: {cfg_goal}

MENU OPTIONS:
{opt_lines}

SYSTEM JUST SAID: {transcript}

Reply with ONLY the single digit to press."""
            try:
                digit = _generate_text_via_bedrock(system_prompt=sys_prompt, user_prompt=user_prompt, max_tokens=20)
            except Exception as e:
                add_to_conversation(call_id, 'warn', f"bedrock_generate_failed: {e}", step_id=step_id, action='agent')
                digit = ''
            digit = (digit or '').strip()
            digit = digit[0] if digit and digit[0].isdigit() else ''
            if digit in options:
                decision = {'action': 'dtmf', 'digits': digit}

        # Keyword-based DTMF fallback if Bedrock can't choose
        if options and cfg_goal and not decision:
            gl = cfg_goal.lower()
            for d, label in options.items():
                ll = (label or '').lower()
                if ('irs' in gl and ('irs' in ll or 'internal revenue' in ll)) or ('mint' in gl and 'mint' in ll) or ('offset' in gl and 'offset' in ll):
                    decision = {'action': 'dtmf', 'digits': d}
                    break

        if not decision:
            sys_prompt = _scenario_persona_prompt(scenario)
            user_prompt = f"""You are the caller in a phone IVR regression test.
GOAL: {cfg_goal or 'Complete the flow and reach a stable end state.'}

SYSTEM JUST SAID: {transcript}

Say what you would say next. Keep it brief (1-2 sentences)."""
            try:
                text = _generate_text_via_bedrock(system_prompt=sys_prompt, user_prompt=user_prompt)
            except Exception as e:
                add_to_conversation(call_id, 'warn', f"bedrock_generate_failed: {e}", step_id=step_id, action='agent')
                text = _goal_to_utterance(goal_first_line) if cfg_goal else "Yes"
            text = (text or '').strip() or (_goal_to_utterance(goal_first_line) if cfg_goal else "Yes")
            decision = {'action': 'speak', 'text': text}

        participant_call_id = call_state.get('participant_call_id', '')
        agent_state = (call_state.get('agent_state') or {}) or {}
        agent_state['turn'] = int(agent_state.get('turn', 0) or 0) + 1
        update_call_state(call_id, {'agent_state': agent_state})

        if decision.get('action') == 'dtmf':
            digits = str(decision.get('digits', '') or '')
            add_to_conversation(call_id, 'dtmf_sent', digits, step_id=step_id, action='agent')
            return create_response([
                {
                    'Type': 'SendDigits',
                    'Parameters': {
                        'CallId': participant_call_id,
                        'Digits': digits,
                        'ToneDurationInMilliseconds': 250,
                        'ToneIntervalInMilliseconds': 250,
                    },
                }
            ])

        text = str(decision.get('text', '') or '').strip() or 'Yes'
        add_to_conversation(call_id, 'caller', text, step_id=step_id, action='agent')
        return create_response([
            {
                'Type': 'Speak',
                'Parameters': {
                    'Text': text,
                    'CallId': participant_call_id,
                    'Engine': 'neural',
                    'LanguageCode': 'en-US',
                    'VoiceId': 'Joanna',
                },
            }
        ])

    if purpose == 'ai_conversation':
        end_patterns = pending.get('end_on_patterns', []) or []
        guidance = pending.get('guidance', '') or ''

        convo_state = (call_state.get('ai_conversation_state') or {}) or {}
        current_turn = int(convo_state.get('turn', 0) or 0)
        end_matched = _match_patterns(transcript, end_patterns)

        # Don't short-circuit before the caller has spoken at least once; otherwise you get a silent "customer".
        if end_matched and current_turn > 0:
            _set_step_outcome(call_id, step_id, {
                'status': 'completed',
                'action': 'ai_conversation',
                'ended_on_pattern': True,
                'matched_patterns': end_matched,
                'transcript': transcript,
            })
            _advance_to_next(call_id, call_state)
            update_call_state(call_id, {'ai_conversation_state': None})
            return generate_next_action(call_id, get_call_state(call_id) or call_state)

        sys_prompt = _scenario_persona_prompt(scenario)
        user_prompt = f"""You are mid-call with an automated system.
SYSTEM JUST SAID: {transcript}

Guidance for this mini-conversation:
{guidance}

Respond as the caller and keep it brief."""

        response_text = ''
        try:
            response_text = _generate_text_via_bedrock(system_prompt=sys_prompt, user_prompt=user_prompt)
        except Exception as e:
            add_to_conversation(call_id, 'warn', f"bedrock_generate_failed: {e}", step_id=step_id, action='ai_conversation')

        if not (response_text or '').strip():
            response_text = "I'm calling to check the status of my tax refund."

        add_to_conversation(call_id, 'caller', response_text, step_id=step_id, action='ai_conversation')

        convo_state = (call_state.get('ai_conversation_state') or {}) or {}
        convo_state['turn'] = int(convo_state.get('turn', 0) or 0) + 1
        update_call_state(call_id, {'ai_conversation_state': convo_state})

        participant_call_id = call_state.get('participant_call_id', '')
        return create_response([
            {
                'Type': 'Speak',
                'Parameters': {
                    'Text': response_text,
                    'CallId': participant_call_id,
                    'Engine': 'neural',
                    'LanguageCode': 'en-US',
                    'VoiceId': 'Joanna',
                },
            }
        ])

    return generate_next_action(call_id, call_state)


def generate_next_action(call_id: str, call_state: Dict[str, Any]) -> Dict[str, Any]:
    call_state = get_call_state(call_id) or call_state

    if (call_state.get('pending_transcription') or {}):
        return _continue_pending_transcription(call_id, call_state)

    scenario = call_state.get('scenario_data', {}) or {}
    steps: List[Dict[str, Any]] = scenario.get('steps', []) or []
    cur_idx = int(call_state.get('current_step_index', 0) or 0)

    # If scenario_data hasn't landed yet (race with TestRunner), wait instead of completing immediately.
    if not steps:
        attempts = int(call_state.get('scenario_wait_attempts', 0) or 0)
        if attempts < 20:
            update_call_state(call_id, {
                'status': 'WAITING_FOR_SCENARIO',
                'scenario_wait_attempts': attempts + 1,
            })
            return create_response([{'Type': 'Pause', 'Parameters': {'DurationInMilliseconds': 500}}])

        update_call_state(call_id, {'status': 'FAILED', 'error': 'scenario_missing'})
        return create_response([{'Type': 'Hangup', 'Parameters': {'SipResponseCode': '500'}}])

    if cur_idx >= len(steps):
        logger.info(f"Scenario complete for call {call_id}")
        update_call_state(call_id, {'status': 'TEST_COMPLETE'})
        return create_response([
            {'Type': 'Pause', 'Parameters': {'DurationInMilliseconds': 500}},
            {'Type': 'Hangup', 'Parameters': {'SipResponseCode': '200'}},
        ])

    step = steps[cur_idx] or {}
    step_id = step.get('id', f"step_{cur_idx}")
    action = step.get('action', 'listen')

    participant_call_id = call_state.get('participant_call_id', '')
    if not participant_call_id and action in ('speak', 'listen', 'dtmf', 'ai_conversation', 'agent'):
        # Try to avoid getting stuck; wait and hope we see Participants in the next event.
        logger.warning(f"Missing participant_call_id for action {action}; pausing")
        return create_response([{'Type': 'Pause', 'Parameters': {'DurationInMilliseconds': 500}}])

    # Enforce max duration
    max_dur = ((scenario.get('target', {}) or {}).get('max_duration_seconds')
               or (scenario.get('target', {}) or {}).get('timeout_seconds')
               or 0)
    if max_dur:
        try:
            started_at = call_state.get('started_at')
            if started_at:
                start_dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                if (datetime.now(timezone.utc) - start_dt).total_seconds() > float(max_dur):
                    update_call_state(call_id, {'status': 'FAILED', 'error': 'max_duration_exceeded'})
                    return create_response([{'Type': 'Hangup', 'Parameters': {'SipResponseCode': '200'}}])
        except Exception:
            pass

    if action == 'speak':
        content = step.get('content', {}) or {}
        ctype = content.get('type', 'literal')

        if ctype == 'literal':
            text = content.get('text', 'Hello')
        elif ctype == 'random_choice':
            choices = content.get('choices', []) or ['Hello']
            text = random.choice(choices)
        else:
            # ai_generated
            intent = content.get('intent', 'Respond naturally and move the scenario forward')
            sys_prompt = _scenario_persona_prompt(scenario)

            # Provide minimal context from the last system utterance
            convo = call_state.get('conversation', []) or []
            last_system = ''
            for turn in reversed(convo):
                if turn.get('speaker') in ('system', 'bot'):
                    last_system = turn.get('text', '')
                    break

            user_prompt = f"""TEST: {scenario.get('name','')}
CURRENT STEP: {step.get('description','')}
INTENT: {intent}
SYSTEM JUST SAID: {last_system}

Say what you would say now."""
            text = _generate_text_via_bedrock(system_prompt=sys_prompt, user_prompt=user_prompt)

        add_to_conversation(call_id, 'caller', text, step_id=step_id, action='speak')
        _set_step_outcome(call_id, step_id, {'status': 'completed', 'action': 'speak'})

        # Advance
        _advance_to_next(call_id, call_state, next_step_id=step.get('next'))

        return create_response([
            {
                'Type': 'Speak',
                'Parameters': {
                    'Text': text,
                    'CallId': participant_call_id,
                    'Engine': 'neural',
                    'LanguageCode': 'en-US',
                    'VoiceId': 'Joanna',
                },
            }
        ])

    if action == 'wait':
        duration_s = float(step.get('duration_seconds', 1) or 1)
        add_to_conversation(call_id, 'wait', f"{duration_s}s", step_id=step_id, action='wait')
        _set_step_outcome(call_id, step_id, {'status': 'completed', 'action': 'wait'})
        _advance_to_next(call_id, call_state, next_step_id=step.get('next'))
        return create_response([
            {'Type': 'Pause', 'Parameters': {'DurationInMilliseconds': int(duration_s * 1000)}}
        ])

    if action == 'dtmf':
        digits = str(step.get('digits', '') or '')
        if not digits:
            add_to_conversation(call_id, 'error', 'dtmf step missing digits', step_id=step_id, action='dtmf')
            _set_step_outcome(call_id, step_id, {'status': 'failed', 'action': 'dtmf', 'error': 'missing_digits'})
            update_call_state(call_id, {'status': 'FAILED', 'error': 'missing_dtmf_digits'})
            return create_response([{'Type': 'Hangup', 'Parameters': {'SipResponseCode': '500'}}])

        add_to_conversation(call_id, 'dtmf_sent', digits, step_id=step_id, action='dtmf')
        _set_step_outcome(call_id, step_id, {'status': 'completed', 'action': 'dtmf', 'digits': digits})
        _advance_to_next(call_id, call_state, next_step_id=step.get('next'))

        return create_response([
            {
                'Type': 'SendDigits',
                'Parameters': {
                    'CallId': participant_call_id,
                    'Digits': digits,
                    'ToneDurationInMilliseconds': 250,
                    'ToneIntervalInMilliseconds': 250,
                },
            }
        ])

    if action == 'hangup':
        reason = step.get('reason', 'completed')
        add_to_conversation(call_id, 'hangup', reason, step_id=step_id, action='hangup')
        _set_step_outcome(call_id, step_id, {'status': 'completed', 'action': 'hangup', 'reason': reason})
        _advance_to_next(call_id, call_state, next_step_id=step.get('next'))
        update_call_state(call_id, {'status': 'TEST_COMPLETE', 'hangup_reason': reason})
        return create_response([
            {'Type': 'Pause', 'Parameters': {'DurationInMilliseconds': 300}},
            {'Type': 'Hangup', 'Parameters': {'SipResponseCode': '200'}},
        ])

    if action == 'listen':
        return start_or_continue_listen(call_id, call_state, step)

    if action == 'ai_conversation':
        return start_or_continue_ai_conversation(call_id, call_state, step)

    if action == 'agent':
        return start_or_continue_agent(call_id, call_state, step)

    # Unknown action
    add_to_conversation(call_id, 'warn', f"Unknown action: {action}")
    _set_step_outcome(call_id, step_id, {'status': 'completed', 'action': action})
    _advance_to_next(call_id, call_state, next_step_id=step.get('next'))
    return create_response([{'Type': 'Pause', 'Parameters': {'DurationInMilliseconds': 500}}])


def start_or_continue_agent(call_id: str, call_state: Dict[str, Any], step: Dict[str, Any]) -> Dict[str, Any]:
    scenario = call_state.get('scenario_data', {}) or {}
    step_id = step.get('id')
    participant_call_id = call_state.get('participant_call_id', '')

    cfg = step.get('config', {}) or {}
    goal = (cfg.get('goal') or step.get('description') or '').strip()

    max_turns = int(cfg.get('max_turns', 12) or 12)
    turn_timeout = int(cfg.get('turn_timeout_seconds', 12) or 12)
    overall_timeout = int(cfg.get('timeout_seconds', 90) or 90)

    success_patterns = cfg.get('success_patterns', []) or []
    end_on_patterns = cfg.get('end_on_patterns', []) or []

    now = time.time()
    agent_state = call_state.get('agent_state', {}) or {}
    if agent_state.get('step_id') != step_id:
        agent_state = {
            'step_id': step_id,
            'turn': 0,
            'deadline_epoch': now + overall_timeout,
            'max_turns': max_turns,
            'turn_timeout_seconds': turn_timeout,
        }

    if now >= float(agent_state.get('deadline_epoch', now)):
        add_to_conversation(call_id, 'system', '(agent timeout)', step_id=step_id, action='agent')
        _set_step_outcome(call_id, step_id, {'status': 'timeout', 'action': 'agent'})
        _advance_to_next(call_id, call_state, next_step_id=step.get('on_timeout') or step.get('next'))
        update_call_state(call_id, {'agent_state': None, 'pending_recording': None})
        return generate_next_action(call_id, get_call_state(call_id) or call_state)

    if int(agent_state.get('turn', 0) or 0) >= max_turns:
        _set_step_outcome(call_id, step_id, {'status': 'completed', 'action': 'agent', 'turns': max_turns})
        _advance_to_next(call_id, call_state, next_step_id=step.get('next'))
        update_call_state(call_id, {'agent_state': None, 'pending_recording': None})
        return generate_next_action(call_id, get_call_state(call_id) or call_state)

    pending = {
        'purpose': 'agent',
        'step_id': step_id,
        'goal': goal,
        'success_patterns': success_patterns,
        'end_on_patterns': end_on_patterns,
        'next_step_id': step.get('next'),
        'turn': int(agent_state.get('turn', 0) or 0),
    }

    test_id = call_state.get('test_id', call_id)
    prefix = f"recordings/{test_id}/snippets/{step_id}/turn_{pending['turn']}_system"

    update_call_state(call_id, {
        'agent_state': agent_state,
        'pending_recording': pending,
    })

    # For agent turns, prefer recording long enough to capture a full prompt.
    dur = min(30, max(DEFAULT_LISTEN_SNIPPET_SECONDS, max(2, turn_timeout)))
    return create_response([
        {
            'Type': 'RecordAudio',
            'Parameters': {
                'CallId': participant_call_id,
                'DurationInSeconds': int(dur),
                'SilenceDurationInSeconds': 2,
                'RecordingDestination': {
                    'Type': 'S3',
                    'BucketName': RECORDINGS_BUCKET,
                    'Prefix': prefix,
                },
                'RecordingTerminators': ['#'],
            },
        }
    ])


def start_or_continue_listen(call_id: str, call_state: Dict[str, Any], step: Dict[str, Any]) -> Dict[str, Any]:
    scenario = call_state.get('scenario_data', {}) or {}
    step_id = step.get('id')
    participant_call_id = call_state.get('participant_call_id', '')

    expect = step.get('expect', {}) or {}
    patterns = expect.get('patterns', []) or []
    timeout_s = int(expect.get('timeout_seconds', 10) or 10)

    now = time.time()
    listen_state = call_state.get('listen_state', {}) or {}
    if listen_state.get('step_id') != step_id:
        listen_state = {
            'step_id': step_id,
            'deadline_epoch': now + timeout_s,
            'attempts': 0,
            'timeout_seconds': timeout_s,
        }

    if now >= float(listen_state.get('deadline_epoch', now)):
        # timeout
        add_to_conversation(call_id, 'system', '(listen timeout)', step_id=step_id, action='listen')
        _set_step_outcome(call_id, step_id, {'status': 'timeout', 'action': 'listen', 'expected_patterns': patterns})

        # Transition
        next_step = step.get('on_timeout') or step.get('on_failure') or step.get('next')
        _advance_to_next(call_id, call_state, next_step_id=next_step)
        update_call_state(call_id, {'listen_state': None, 'pending_recording': None})
        return generate_next_action(call_id, get_call_state(call_id) or call_state)

    # Record a snippet
    listen_state['attempts'] = int(listen_state.get('attempts', 0) or 0) + 1
    pending = {
        'purpose': 'listen',
        'step_id': step_id,
        'expected_patterns': patterns,
    }

    test_id = call_state.get('test_id', call_id)
    prefix = f"recordings/{test_id}/snippets/{step_id}/attempt_{listen_state['attempts']}"

    update_call_state(call_id, {
        'listen_state': listen_state,
        'pending_recording': pending,
    })

    deadline_epoch = float(listen_state.get('deadline_epoch', now))
    dur = min(DEFAULT_LISTEN_SNIPPET_SECONDS, max(1, int(deadline_epoch - float(now))))

    return create_response([
        {
            'Type': 'RecordAudio',
            'Parameters': {
                'CallId': participant_call_id,
                'DurationInSeconds': int(dur),
                'SilenceDurationInSeconds': 2,
                'RecordingDestination': {
                    'Type': 'S3',
                    'BucketName': RECORDINGS_BUCKET,
                    'Prefix': prefix,
                },
                'RecordingTerminators': ['#'],
            },
        }
    ])


def start_or_continue_ai_conversation(call_id: str, call_state: Dict[str, Any], step: Dict[str, Any]) -> Dict[str, Any]:
    step_id = step.get('id')
    participant_call_id = call_state.get('participant_call_id', '')
    cfg = step.get('config', {}) or {}

    max_turns = int(cfg.get('max_turns', 3) or 3)
    turn_timeout = int(cfg.get('turn_timeout_seconds', 20) or 20)

    convo_state = call_state.get('ai_conversation_state', {}) or {}
    if convo_state.get('step_id') != step_id:
        convo_state = {
            'step_id': step_id,
            'turn': 0,
            'max_turns': max_turns,
            'turn_timeout_seconds': turn_timeout,
        }

    if int(convo_state.get('turn', 0) or 0) >= max_turns:
        _set_step_outcome(call_id, step_id, {'status': 'completed', 'action': 'ai_conversation', 'turns': max_turns})
        _advance_to_next(call_id, call_state, next_step_id=step.get('next'))
        update_call_state(call_id, {'ai_conversation_state': None, 'pending_recording': None})
        return generate_next_action(call_id, get_call_state(call_id) or call_state)

    # If we arrived here right after a listen step that already captured the system prompt,
    # speak first so the IVR hears the caller (otherwise we can sit silently and miss the prompt).
    if int(convo_state.get('turn', 0) or 0) == 0 and not convo_state.get('opening_spoken'):
        convo = call_state.get('conversation', []) or []
        last_system = ''
        for t in reversed(convo):
            if t.get('speaker') in ('system', 'bot'):
                last_system = (t.get('text') or '').strip()
                if last_system:
                    break

        if last_system:
            scenario = call_state.get('scenario_data', {}) or {}
            guidance = (cfg.get('guidance', '') or '').strip()
            sys_prompt = _scenario_persona_prompt(scenario)
            user_prompt = f"""You are mid-call with an automated system.
SYSTEM JUST SAID: {last_system}

Guidance for this mini-conversation:
{guidance}

Respond as the caller and keep it brief."""

            response_text = ''
            try:
                response_text = _generate_text_via_bedrock(system_prompt=sys_prompt, user_prompt=user_prompt)
            except Exception as e:
                add_to_conversation(call_id, 'warn', f"bedrock_generate_failed: {e}", step_id=step_id, action='ai_conversation')

            if not (response_text or '').strip():
                response_text = "I'm calling to check the status of my tax refund."

            add_to_conversation(call_id, 'caller', response_text, step_id=step_id, action='ai_conversation')
            convo_state['turn'] = int(convo_state.get('turn', 0) or 0) + 1
            convo_state['opening_spoken'] = True
            update_call_state(call_id, {'ai_conversation_state': convo_state})

            return create_response([
                {
                    'Type': 'Speak',
                    'Parameters': {
                        'Text': response_text,
                        'CallId': participant_call_id,
                        'Engine': 'neural',
                        'LanguageCode': 'en-US',
                        'VoiceId': 'Joanna',
                    },
                }
            ])

    pending = {
        'purpose': 'ai_conversation',
        'step_id': step_id,
        'turn': int(convo_state.get('turn', 0) or 0),
        'end_on_patterns': cfg.get('end_on_patterns', []) or [],
        'guidance': cfg.get('guidance', '') or '',
    }

    test_id = call_state.get('test_id', call_id)
    prefix = f"recordings/{test_id}/snippets/{step_id}/turn_{pending['turn']}_system"

    update_call_state(call_id, {
        'ai_conversation_state': convo_state,
        'pending_recording': pending,
    })

    dur = min(DEFAULT_LISTEN_SNIPPET_SECONDS, max(2, turn_timeout))

    return create_response([
        {
            'Type': 'RecordAudio',
            'Parameters': {
                'CallId': participant_call_id,
                'DurationInSeconds': int(dur),
                'SilenceDurationInSeconds': 2,
                'RecordingDestination': {
                    'Type': 'S3',
                    'BucketName': RECORDINGS_BUCKET,
                    'Prefix': prefix,
                },
                'RecordingTerminators': ['#'],
            },
        }
    ])


def handle_record_audio_success(call_id: str, call_state: Dict[str, Any], action_data: Dict[str, Any]) -> Dict[str, Any]:
    pending = call_state.get('pending_recording', {}) or {}
    purpose = pending.get('purpose')
    step_id = pending.get('step_id')

    rec_dest = (action_data.get('RecordingDestination') or {})
    bucket = rec_dest.get('BucketName') or RECORDINGS_BUCKET
    key = rec_dest.get('Key')

    if not (bucket and key and purpose and step_id):
        add_to_conversation(call_id, 'error', f"RecordAudio missing destination/pending info: {pending}")
        update_call_state(call_id, {'status': 'FAILED', 'error': 'recordaudio_missing_destination'})
        return create_response([{'Type': 'Hangup', 'Parameters': {'SipResponseCode': '500'}}])

    # Start an async Transcribe job (fast) and poll via Pause events (keeps SMA handler quick).
    deadline_epoch = None
    if purpose == 'listen':
        deadline_epoch = (call_state.get('listen_state', {}) or {}).get('deadline_epoch')
    elif purpose == 'ai_conversation':
        deadline_epoch = time.time() + 25
    elif purpose == 'agent':
        deadline_epoch = time.time() + 25

    try:
        job_name = _start_transcribe_job_for_s3_wav(bucket=bucket, key=key, sample_rate=8000)
    except Exception as e:
        add_to_conversation(call_id, 'error', f"transcribe_start_failed: {e}", step_id=step_id, action=purpose)
        update_call_state(call_id, {'status': 'FAILED', 'error': f'transcribe_start_failed: {e}'})
        return create_response([{'Type': 'Hangup', 'Parameters': {'SipResponseCode': '500'}}])

    update_call_state(call_id, {
        'pending_recording': None,
        'pending_transcription': {
            'job_name': job_name,
            'purpose': purpose,
            'step_id': step_id,
            'expected_patterns': pending.get('expected_patterns', []) or [],
            'end_on_patterns': pending.get('end_on_patterns', []) or [],
            'guidance': pending.get('guidance', '') or '',
            'deadline_epoch': deadline_epoch,
        },
    })

    return create_response([{'Type': 'Pause', 'Parameters': {'DurationInMilliseconds': 500}}])


def evaluate_success_criteria(scenario: Dict[str, Any], call_state: Dict[str, Any]) -> Dict[str, Any]:
    criteria = (scenario.get('success_criteria', {}) or {}).get('required', []) or []
    outcomes = call_state.get('step_outcomes', {}) or {}

    results = []
    passed = True

    for c in criteria:
        step_id = c.get('step')
        expected = c.get('status', 'completed')
        actual = (outcomes.get(step_id) or {}).get('status')
        ok = (actual == expected)
        if not ok:
            passed = False
        results.append({
            'step': step_id,
            'expected': expected,
            'actual': actual,
            'passed': ok,
        })

    return {
        'passed': passed,
        'required': results,
    }


# =============================================================================
# DynamoDB helpers
# =============================================================================

def get_call_state(call_id: str) -> Optional[Dict[str, Any]]:
    table = _dynamodb.Table(CALL_STATE_TABLE)
    try:
        response = table.get_item(Key={'call_id': call_id})
        return response.get('Item')
    except Exception as e:
        logger.error(f"Error getting call state: {e}")
        return None


def update_call_state(call_id: str, updates: Dict[str, Any]) -> None:
    table = _dynamodb.Table(CALL_STATE_TABLE)

    # DynamoDB does not accept float types; convert them to Decimal.
    from decimal import Decimal

    def _to_dynamo(v: Any) -> Any:
        if isinstance(v, float):
            return Decimal(str(v))
        if isinstance(v, dict):
            return {k: _to_dynamo(x) for k, x in v.items()}
        if isinstance(v, list):
            return [_to_dynamo(x) for x in v]
        return v

    update_expr_parts = []
    expr_attr_values: Dict[str, Any] = {}
    expr_attr_names: Dict[str, str] = {}

    for key, value in updates.items():
        safe_key = f"#{key}"
        expr_attr_names[safe_key] = key
        expr_attr_values[f":{key}"] = _to_dynamo(value)
        update_expr_parts.append(f"{safe_key} = :{key}")

    if not update_expr_parts:
        return

    try:
        table.update_item(
            Key={'call_id': call_id},
            UpdateExpression="SET " + ", ".join(update_expr_parts),
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values,
        )
    except Exception as e:
        logger.error(f"Error updating call state: {e}")


def add_to_conversation(call_id: str, speaker: str, text: str, *, step_id: Optional[str] = None, action: Optional[str] = None) -> None:
    table = _dynamodb.Table(CALL_STATE_TABLE)

    entry: Dict[str, Any] = {
        'timestamp': _utcnow_iso(),
        'speaker': speaker,
        'text': text,
    }
    if step_id:
        entry['step_id'] = step_id
    if action:
        entry['action'] = action

    try:
        table.update_item(
            Key={'call_id': call_id},
            UpdateExpression="SET conversation = list_append(if_not_exists(conversation, :empty), :entry)",
            ExpressionAttributeValues={
                ':entry': [entry],
                ':empty': [],
            },
        )
    except Exception as e:
        logger.error(f"Error adding to conversation: {e}")


def save_test_results(call_state: Dict[str, Any]) -> None:
    table = _dynamodb.Table(TEST_RESULTS_TABLE)

    test_id = call_state.get('test_id', call_state.get('call_id'))
    timestamp = call_state.get('results_timestamp') or call_state.get('started_at') or _utcnow_iso()

    key = {'test_id': test_id, 'timestamp': timestamp}

    # Merge into the existing TestRunner-created row (preserves target_number, etc.)
    existing: Dict[str, Any] = {}
    try:
        existing = (table.get_item(Key=key) or {}).get('Item') or {}
    except Exception:
        existing = {}

    test_result = {
        **existing,
        'test_id': test_id,
        'timestamp': timestamp,
        'scenario_name': call_state.get('scenario_name', existing.get('scenario_name', 'unknown')),
        'call_id': call_state.get('call_id', existing.get('call_id', '')),
        'transaction_id': call_state.get('call_id', existing.get('transaction_id', '')),
        'status': call_state.get('status', existing.get('status', 'UNKNOWN')),
        'started_at': call_state.get('started_at', existing.get('started_at')),
        'ended_at': call_state.get('ended_at', existing.get('ended_at')),
        'conversation': call_state.get('conversation', existing.get('conversation', [])),
        'step_outcomes': call_state.get('step_outcomes', existing.get('step_outcomes', {})),
        'evaluation': call_state.get('evaluation', existing.get('evaluation', {})),
        'recording_path': (
            f"s3://{RECORDINGS_BUCKET}/recordings/{test_id}/" if RECORDINGS_BUCKET else ''
        ),
    }

    try:
        table.put_item(Item=test_result)
        logger.info(f"Test results saved: {test_id}")
    except Exception as e:
        logger.error(f"Error saving test results: {e}")
