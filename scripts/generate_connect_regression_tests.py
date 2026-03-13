#!/usr/bin/env python3
"""Generate Amazon Connect regression test manifest + scenario stubs.

What this does:
- Enumerates Connect instances in specified regions
- Enumerates claimed phone numbers (ListPhoneNumbersV2) and groups them by instance
- Enumerates contact flows (CONTACT_FLOW) and extracts lightweight "analysis" from flow content
- Links existing PSTN scenario YAMLs that already cover each claimed phone number
- Creates a PSTN smoke-test scenario for any claimed phone number without coverage

Notes:
- Amazon Connect exposes read APIs for voice-number → flow association via ListFlowAssociations
  (ResourceType=VOICE_PHONE_NUMBER), which returns ResourceId=phone-number ARN and FlowId=contact-flow ARN.
  This script uses that mapping when available.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import boto3


DEFAULT_REGIONS = ["us-east-1", "us-west-2"]


def redact_e164(e164: str) -> str:
    if not e164:
        return e164
    return re.sub(r"\d(?=\d{2})", "X", e164)


def safe_json_loads(s: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(s)
    except Exception:
        return None


def arn_tail(arn: Optional[str]) -> Optional[str]:
    if not arn or not isinstance(arn, str):
        return None
    return arn.rsplit("/", 1)[-1] if "/" in arn else arn


def list_all_pages(fn, list_key: str, token_key: str = "NextToken", **kwargs) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    token: Optional[str] = None
    while True:
        call_kwargs = dict(kwargs)
        if token:
            call_kwargs[token_key] = token
        resp = fn(**call_kwargs)
        out.extend(resp.get(list_key, []))
        token = resp.get(token_key)
        if not token:
            break
    return out


def find_scenarios_by_phone(scenarios_root: Path) -> Dict[str, List[str]]:
    """Map E.164 phone number -> list of scenario paths (relative to repo root) that mention it."""
    mapping: Dict[str, List[str]] = {}
    if not scenarios_root.exists():
        return mapping

    for p in sorted(scenarios_root.rglob("*.y*ml")):
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # Very simple scan: phone_number: "+1..."
        for m in re.finditer(r"phone_number\s*:\s*\"(?P<num>\+\d{8,15})\"", txt):
            num = m.group("num")
            mapping.setdefault(num, []).append(str(p))

    return mapping


def build_pstn_smoke_scenario(
    *,
    name: str,
    description: str,
    phone_number: str,
    instance_id: str,
    instance_alias: str,
    region: str,
    phone_number_id: str,
    phone_number_arn: str,
    phone_number_description: str,
    inbound_flow_id: str = "",
    inbound_flow_arn: str = "",
    inbound_flow_name: str = "",
) -> Dict[str, Any]:
    """Create a minimal PSTN smoke scenario that should be safe across unknown IVRs."""
    return {
        "name": name,
        "version": "1.0.0",
        "description": description,
        "author": "Copilot CLI (generated)",
        "created": datetime.utcnow().strftime("%Y-%m-%d"),
        "tags": ["connect", "pstn", "smoke", "generated"],
        "connection": {"mode": "pstn"},
        "target": {
            "phone_number": phone_number,
            "timeout_seconds": 45,
            "max_duration_seconds": 60,
            "recording": {"enabled": True, "format": "wav", "channels": 2},
            # Metadata (not required by runner)
            "instance_id": instance_id,
            "instance_alias": instance_alias,
            "region": region,
            "phone_number_id": phone_number_id,
            "phone_number_arn": phone_number_arn,
            "phone_number_description": phone_number_description,
            # Inbound flow association (when available)
            "contact_flow_id": inbound_flow_id,
            "contact_flow_arn": inbound_flow_arn,
            "contact_flow_name": inbound_flow_name,
        },
        "persona": {
            "name": "Smoke Test Caller",
            "system_prompt": (
                "You are making a brief test call to verify the line answers and plays any prompt. "
                "Be polite, keep responses short, and do not provide sensitive information."
            ),
            "attributes": {"speaking_rate": "normal", "patience": "patient", "clarity": "clear"},
        },
        "steps": [
            {
                "id": "wait_for_any_audio",
                "description": "Wait for any greeting or audio from the IVR",
                "action": "listen",
                "expect": {
                    "patterns": [
                        "welcome",
                        "thank you",
                        "hello",
                        "press",
                        "menu",
                        "calling",
                    ],
                    "timeout_seconds": 30,
                },
                "on_timeout": "hangup_timeout",
            },
            {
                "id": "hangup_normal",
                "description": "End the smoke test call",
                "action": "hangup",
                "reason": "completed",
            },
            {
                "id": "hangup_timeout",
                "description": "End the call if no audio is detected",
                "action": "hangup",
                "reason": "timeout",
            },
        ],
        "success_criteria": {
            "required": [{"step": "wait_for_any_audio", "status": "matched"}],
            "call_duration": {"min_seconds": 5, "max_seconds": 60},
        },
        "assertions": [
            {
                "type": "transcript_excludes",
                "description": "No explicit error prompts",
                "patterns": ["system error", "cannot process", "unavailable"],
            }
        ],
        "metadata": {
            "connect_instance": instance_alias,
            "connect_region": region,
            "phone_number_id": phone_number_id,
            "inbound_flow_id": inbound_flow_id,
            "inbound_flow_arn": inbound_flow_arn,
            "inbound_flow_name": inbound_flow_name,
        },
    }


def analyze_flow_content(content: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not content:
        return {"action_count": None, "prompts": [], "lex_bots": [], "errors": ["no_content"]}

    actions = content.get("Actions", []) if isinstance(content, dict) else []
    prompts: List[str] = []
    lex_bots: List[str] = []

    for a in actions if isinstance(actions, list) else []:
        a_type = (a or {}).get("Type", "")
        params = (a or {}).get("Parameters", {}) or {}

        # Common patterns seen in sample flow JSON
        txt = params.get("Text") or params.get("PromptText")
        if isinstance(txt, str) and txt.strip():
            prompts.append(txt.strip())

        if a_type == "ConnectParticipantWithLexBot":
            bot = params.get("LexBot", {}) or {}
            name = bot.get("Name")
            if name:
                lex_bots.append(name)

    # Trim for manifest readability
    return {
        "action_count": len(actions) if isinstance(actions, list) else None,
        "prompts": prompts[:10],
        "lex_bots": sorted(set(lex_bots)),
        "errors": [],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--regions",
        nargs="+",
        default=DEFAULT_REGIONS,
        help="Connect regions to scan (default: us-east-1 us-west-2)",
    )
    ap.add_argument(
        "--out-dir",
        default=None,
        help="Output directory for manifest + generated scenarios (default: voice_tester/scenarios/instance_tests/generated/connect_regression_YYYY-MM-DD)",
    )
    ap.add_argument(
        "--scenarios-root",
        default="voice_tester/scenarios/instance_tests",
        help="Where to look for existing PSTN scenario coverage",
    )
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    scenarios_root = (repo_root / args.scenarios_root).resolve()

    today = datetime.utcnow().strftime("%Y-%m-%d")
    out_dir = Path(args.out_dir) if args.out_dir else (repo_root / "voice_tester/scenarios/instance_tests/generated" / f"connect_regression_{today}")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Map phone number -> scenario file paths that already contain it
    scenario_map = find_scenarios_by_phone(scenarios_root)

    sess = boto3.session.Session()

    manifest: Dict[str, Any] = {
        "generated_at": today,
        "regions_scanned": list(args.regions),
        "instances": [],
        "phone_numbers": [],
        "flows": [],
        "scenarios": [],
        "notes": {
            "phone_to_flow_association": (
                "This manifest attempts to map each claimed VOICE phone number to its inbound contact flow using ListFlowAssociations (ResourceType=VOICE_PHONE_NUMBER), "
                "which returns ResourceId=phone-number ARN and FlowId=contact-flow ARN. Where no association is returned, the inbound flow may be unset or not discoverable for that number in this region/instance context."
            )
        },
    }

    for region in args.regions:
        connect = sess.client("connect", region_name=region)

        # Instances
        instances = list_all_pages(connect.list_instances, "InstanceSummaryList", MaxResults=100)
        instances = [i for i in instances if i.get("InstanceStatus") == "ACTIVE"]

        # Phone numbers (account/region scoped)
        nums = list_all_pages(connect.list_phone_numbers_v2, "ListPhoneNumbersSummaryList", MaxResults=25)
        nums_by_instance: Dict[str, List[Dict[str, Any]]] = {}
        for n in nums:
            iid = n.get("InstanceId")
            if iid:
                nums_by_instance.setdefault(iid, []).append(n)

        for inst in instances:
            iid = inst.get("Id")
            alias = inst.get("InstanceAlias", "")
            i_arn = inst.get("Arn")

            # Phone number -> inbound flow associations (VOICE_PHONE_NUMBER)
            phone_arn_to_flow_arn: Dict[str, str] = {}
            try:
                assocs = list_all_pages(
                    connect.list_flow_associations,
                    "FlowAssociationSummaryList",
                    InstanceId=iid,
                    ResourceType="VOICE_PHONE_NUMBER",
                    MaxResults=1000,
                )
                for a in assocs:
                    rid = a.get("ResourceId")
                    fid = a.get("FlowId")
                    if rid and fid:
                        phone_arn_to_flow_arn[rid] = fid
            except Exception:
                # Best-effort: older permissions/models may not allow this call.
                phone_arn_to_flow_arn = {}

            # Contact flows
            flows = list_all_pages(
                connect.list_contact_flows,
                "ContactFlowSummaryList",
                InstanceId=iid,
                ContactFlowTypes=["CONTACT_FLOW"],
                MaxResults=100,
            )
            flow_id_to_name = {f.get("Id"): f.get("Name") for f in flows if f.get("Id")}

            # Minimal analysis for non-sample flows
            custom_flows = [
                f
                for f in flows
                if f.get("Name")
                and "Sample" not in f.get("Name", "")
                and "Default" not in f.get("Name", "")
            ]
            analyzed_custom: List[Dict[str, Any]] = []
            for f in sorted(custom_flows, key=lambda x: x.get("Name", "")):
                fid = f.get("Id")
                try:
                    d = connect.describe_contact_flow(InstanceId=iid, ContactFlowId=fid)
                    cf = d.get("ContactFlow", {})
                    content = safe_json_loads(cf.get("Content", "")) if isinstance(cf.get("Content"), str) else None
                    analysis = analyze_flow_content(content)
                except Exception as e:
                    analysis = {"action_count": None, "prompts": [], "lex_bots": [], "errors": [str(e)]}

                analyzed_custom.append(
                    {
                        "region": region,
                        "instance_id": iid,
                        "instance_alias": alias,
                        "contact_flow_id": fid,
                        "name": f.get("Name"),
                        "type": f.get("ContactFlowType"),
                        "analysis": analysis,
                    }
                )

            # Phone numbers for this instance
            inst_nums = nums_by_instance.get(iid, [])
            normalized_nums = []
            for n in inst_nums:
                pn_arn = n.get("PhoneNumberArn")
                inbound_flow_arn = phone_arn_to_flow_arn.get(pn_arn) if pn_arn else None
                inbound_flow_id = arn_tail(inbound_flow_arn) if inbound_flow_arn else None
                normalized_nums.append(
                    {
                        "region": region,
                        "instance_id": iid,
                        "instance_alias": alias,
                        "phone_number": n.get("PhoneNumber"),
                        "phone_number_id": n.get("PhoneNumberId"),
                        "phone_number_arn": pn_arn,
                        "phone_number_type": n.get("PhoneNumberType"),
                        "phone_number_description": n.get("PhoneNumberDescription", ""),
                        "target_arn": n.get("TargetArn"),
                        "inbound_flow_arn": inbound_flow_arn,
                        "inbound_flow_id": inbound_flow_id,
                        "inbound_flow_name": flow_id_to_name.get(inbound_flow_id) if inbound_flow_id else None,
                    }
                )

            manifest["instances"].append(
                {
                    "region": region,
                    "instance_id": iid,
                    "instance_alias": alias,
                    "instance_arn": i_arn,
                    "instance_status": inst.get("InstanceStatus"),
                    "phone_numbers": [
                        {
                            "phone_number": x["phone_number"],
                            "phone_number_id": x["phone_number_id"],
                            "phone_number_type": x["phone_number_type"],
                            "phone_number_description": x["phone_number_description"],
                            "inbound_flow_id": x.get("inbound_flow_id"),
                            "inbound_flow_name": x.get("inbound_flow_name"),
                        }
                        for x in normalized_nums
                    ],
                    "custom_contact_flows": [
                        {"name": x["name"], "contact_flow_id": x["contact_flow_id"], "type": x["type"]}
                        for x in analyzed_custom
                    ],
                }
            )

            manifest["phone_numbers"].extend(normalized_nums)
            manifest["flows"].extend(analyzed_custom)

    # Link or generate scenarios per phone number
    generated: List[str] = []
    for pn in manifest["phone_numbers"]:
        e164 = pn.get("phone_number") or ""
        existing = scenario_map.get(e164, [])
        manifest["scenarios"].append(
            {
                "phone_number": e164,
                "phone_number_redacted": redact_e164(e164),
                "instance_alias": pn.get("instance_alias"),
                "instance_id": pn.get("instance_id"),
                "region": pn.get("region"),
                "existing_scenarios": existing,
                "generated_scenarios": [],
            }
        )

        # Always generate a smoke scenario so the PSTN suite can run uniformly across all claimed numbers,
        # even when other (legacy) scenarios already exist.
        scen_name = f"Connect PSTN Smoke - {pn.get('instance_alias','instance')}"
        file_stem = f"pstn_smoke_{pn.get('instance_alias','instance')}_{pn.get('phone_number_id','number')}"
        file_stem = re.sub(r"[^a-zA-Z0-9_\-]+", "_", file_stem).strip("_")
        out_path = out_dir / f"{file_stem}.yaml"

        if out_path.exists():
            manifest["scenarios"][-1]["generated_scenarios"].append(str(out_path))
            continue

        scenario = build_pstn_smoke_scenario(
            name=scen_name,
            description=(
                "Generated smoke regression test: verifies the line answers and plays an IVR prompt. "
                "This is intentionally minimal until a real baseline transcript is captured."
            ),
            phone_number=e164,
            instance_id=pn.get("instance_id", ""),
            instance_alias=pn.get("instance_alias", ""),
            region=pn.get("region", ""),
            phone_number_id=pn.get("phone_number_id", ""),
            phone_number_arn=pn.get("phone_number_arn", ""),
            phone_number_description=pn.get("phone_number_description", ""),
            inbound_flow_id=pn.get("inbound_flow_id") or "",
            inbound_flow_arn=pn.get("inbound_flow_arn") or "",
            inbound_flow_name=pn.get("inbound_flow_name") or "",
        )

        import yaml  # local import so script still imports if yaml missing in unrelated environments

        out_path.write_text(yaml.safe_dump(scenario, sort_keys=False, allow_unicode=True), encoding="utf-8")
        generated.append(str(out_path))

        # Update manifest entry
        manifest["scenarios"][-1]["generated_scenarios"].append(str(out_path))

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Console summary (redacted)
    print(f"Wrote: {manifest_path}")
    for pn in manifest["phone_numbers"]:
        print(
            f"{pn.get('region')}\t{pn.get('instance_alias')}\t{redact_e164(pn.get('phone_number') or '')}\t" \
            f"existing_tests={len(scenario_map.get(pn.get('phone_number') or '', []))}"
        )
    for g in generated:
        # avoid printing full number content
        print(f"Generated scenario: {Path(g).name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
