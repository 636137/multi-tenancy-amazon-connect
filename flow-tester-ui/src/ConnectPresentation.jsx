import { useState } from "react";

const C = {
  bg: "#0a0e1a", surface: "#111827", surfaceLight: "#1a2235",
  accent: "#00d4ff", accentDim: "#00d4ff33",
  danger: "#ff3b5c", dangerDim: "#ff3b5c22",
  success: "#00e68a", successDim: "#00e68a22",
  warn: "#ffb020", warnDim: "#ffb02022",
  purple: "#a78bfa", purpleDim: "#a78bfa22",
  rose: "#fb7185", roseDim: "#fb718522",
  teal: "#2dd4bf", tealDim: "#2dd4bf22",
  amber: "#f59e0b",
  slate: "#64748b",
  text: "#e2e8f0", textDim: "#94a3b8",
  border: "#1e293b", borderLight: "#334155",
};
const T = [
  { name: "HMRC", color: "#00d4ff", icon: "£" },
  { name: "NHS Digital", color: "#00e68a", icon: "+" },
  { name: "DWP", color: "#ffb020", icon: "◆" },
  { name: "Home Office", color: "#a78bfa", icon: "⬡" },
];
const SL = [
  { id: "hero", label: "Overview" }, { id: "shared", label: "Shared Instance" },
  { id: "tagging", label: "Tag Reality" }, { id: "domains", label: "Domain Locks" },
  { id: "gaps", label: "TBAC Gaps" }, { id: "ai", label: "AI Bundle" },
  { id: "technical", label: "Technical Path" }, { id: "business", label: "Business Decision" },
  { id: "faq", label: "FAQ" }, { id: "solution", label: "Per-Agency" },
];
const F = "'DM Sans', sans-serif";
const FH = "'Playfair Display', Georgia, serif";

function Badge({ children, color = C.accent }) {
  return <span style={{ display: "inline-block", padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 700, letterSpacing: 0.8, color, border: `1px solid ${color}44`, background: `${color}15`, textTransform: "uppercase" }}>{children}</span>;
}
function Orb({ color, size = 200, top, left, opacity = 0.12 }) {
  return <div style={{ position: "absolute", top, left, width: size, height: size, borderRadius: "50%", filter: "blur(80px)", opacity, background: color, pointerEvents: "none", zIndex: 0 }} />;
}
function Pulse({ color }) {
  return <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: color, marginRight: 8, verticalAlign: "middle", animation: "pulse 2s ease-in-out infinite" }} />;
}
function Sl({ visible, children }) {
  return <div style={{ padding: "28px 20px", opacity: 1, visibility: "visible" }}>{children}</div>;
}
function SH({ badge, bc, title, hl, hc, sub }) {
  return (
    <div style={{ textAlign: "center", marginBottom: 26, position: "relative", zIndex: 1 }}>
      <Badge color={bc}>{badge}</Badge>
      <h2 style={{ fontSize: 30, fontWeight: 800, color: C.text, margin: "14px 0 6px", fontFamily: FH, lineHeight: 1.15 }}>
        {title} <span style={{ color: hc }}>{hl}</span>
      </h2>
      {sub && <p style={{ fontSize: 13, color: C.textDim, maxWidth: 560, margin: "0 auto", fontFamily: F, lineHeight: 1.5 }}>{sub}</p>}
    </div>
  );
}

// 1. HERO
function S1({ v }) {
  return (
    <Sl visible={v}>
      <Orb color={C.accent} size={400} top={-100} left={-100} opacity={0.07} />
      <Orb color={C.danger} size={300} top={200} left="60%" opacity={0.05} />
      <div style={{ textAlign: "center", padding: "50px 0 30px", position: "relative", zIndex: 1 }}>
        <Badge color={C.warn}>UK Government Risk Analysis</Badge>
        <h1 style={{ fontSize: 48, fontWeight: 800, color: C.text, margin: "22px 0 0", fontFamily: FH, lineHeight: 1.1, letterSpacing: -1 }}>Multi-Tenant<br /><span style={{ color: C.accent }}>Amazon Connect</span></h1>
        <p style={{ fontSize: 16, color: C.textDim, maxWidth: 540, margin: "18px auto 0", lineHeight: 1.6, fontFamily: F }}>How tag-based access controls, domain constraints, and the AI pricing toggle interact across sovereign government entities — and where isolation fails.</p>
        <div style={{ display: "flex", gap: 14, justifyContent: "center", marginTop: 40, flexWrap: "wrap" }}>
          {T.map((t, i) => (
            <div key={t.name} style={{ padding: "12px 20px", borderRadius: 12, border: `1px solid ${t.color}33`, background: `${t.color}08`, display: "flex", alignItems: "center", gap: 10, opacity: 1 }}>
              <span style={{ fontSize: 18, width: 30, height: 30, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", background: `${t.color}22`, color: t.color }}>{t.icon}</span>
              <span style={{ color: t.color, fontWeight: 600, fontSize: 13, fontFamily: F }}>{t.name}</span>
            </div>
          ))}
        </div>
        <p style={{ fontSize: 12, color: C.textDim, marginTop: 28, opacity: 0.5, fontFamily: F }}>4 independent data controllers · 1 shared instance · 6+ data repos · 1 domain each for Profiles, Cases, Q</p>
      </div>
    </Sl>
  );
}

// 2. SHARED INSTANCE
function S2({ v }) {
  const repos = [{ n: "S3 Recordings", i: "🪣", d: "Call recordings & transcripts" }, { n: "Contact Records", i: "📋", d: "CTRs via shared Kinesis" }, { n: "Contact Lens", i: "🔍", d: "Analytics & sentiment" }, { n: "Lex Sessions", i: "🤖", d: "Bot conversation logs" }, { n: "DynamoDB", i: "🗃️", d: "Session state & config" }, { n: "CloudWatch", i: "📊", d: "Metrics & ops logs" }];
  return (
    <Sl visible={v}>
      <Orb color={C.danger} size={300} top={-50} left="70%" opacity={0.05} />
      <SH badge="Architecture Problem" bc={C.danger} title="One Instance," hl="Shared Everything" hc={C.danger} sub="All tenants' data flows into common AWS resources with no native isolation" />
      <div style={{ display: "flex", justifyContent: "center", gap: 10, marginBottom: 6, flexWrap: "wrap", position: "relative", zIndex: 1 }}>
        {T.map((t, i) => (<div key={t.name} style={{ padding: "8px 16px", borderRadius: 10, border: `1px solid ${t.color}44`, background: `${t.color}10`, textAlign: "center", minWidth: 90, opacity: 1 }}><div style={{ fontSize: 16, color: t.color }}>{t.icon}</div><div style={{ fontSize: 11, fontWeight: 700, color: t.color, fontFamily: F }}>{t.name}</div></div>))}
      </div>
      <div style={{ display: "flex", justifyContent: "center", margin: "6px 0", position: "relative", zIndex: 1 }}>
        {T.map((t, i) => (<div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 90 }}><div style={{ width: 2, height: 20, background: `linear-gradient(to bottom, ${t.color}66, ${C.warn}66)` }} /><div style={{ width: 0, height: 0, borderLeft: "4px solid transparent", borderRight: "4px solid transparent", borderTop: `5px solid ${C.warn}88` }} /></div>))}
      </div>
      <div style={{ border: `2px solid ${C.danger}44`, borderRadius: 14, padding: "16px", background: `linear-gradient(135deg, ${C.dangerDim}, ${C.surface})`, position: "relative", zIndex: 1, maxWidth: 680, margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}><Pulse color={C.danger} /><span style={{ fontSize: 12, fontWeight: 700, color: C.danger, letterSpacing: 1, textTransform: "uppercase", fontFamily: F }}>Shared Amazon Connect Instance</span></div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 8 }}>
          {repos.map((r, i) => (<div key={r.n} style={{ padding: "10px 12px", borderRadius: 10, border: `1px solid ${C.borderLight}`, background: C.surface, opacity: 1 }}><div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}><span style={{ fontSize: 16 }}>{r.i}</span><span style={{ fontSize: 11, fontWeight: 700, color: C.text, fontFamily: F }}>{r.n}</span></div><div style={{ fontSize: 10, color: C.textDim, lineHeight: 1.4, fontFamily: F }}>{r.d}</div><div style={{ display: "flex", gap: 3, marginTop: 6 }}>{T.map(t => <span key={t.name} style={{ width: 7, height: 7, borderRadius: 2, background: t.color, opacity: 0.7 }} />)}<span style={{ fontSize: 8, color: C.textDim, marginLeft: 3, fontFamily: F }}>mixed</span></div></div>))}
        </div>
        <div style={{ marginTop: 10, padding: "8px 12px", borderRadius: 8, background: `${C.danger}10`, border: `1px solid ${C.danger}22`, fontSize: 11, color: C.danger, lineHeight: 1.5, fontFamily: F }}>⚠ Every repository contains commingled data from all tenants. No native partition boundary.</div>
      </div>
    </Sl>
  );
}

// 3. TAGGING
function S3({ v }) {
  const res = [
    { n: "Users / Agents", tg: true, tb: true }, { n: "Queues", tg: true, tb: true }, { n: "Routing Profiles", tg: true, tb: true },
    { n: "Contacts", tg: false, tb: false, c: true }, { n: "Contact Lens Dashboard", tg: true, tb: false, c: true },
    { n: "Contact Search", tg: true, tb: "p", c: true }, { n: "S3 Recordings", tg: false, tb: false, c: true },
    { n: "Kinesis Streams", tg: false, tb: false }, { n: "CloudWatch Logs", tg: false, tb: false },
    { n: "Real-time Metrics", tg: true, tb: true }, { n: "Historical Metrics", tg: true, tb: true }, { n: "Security Profiles", tg: true, tb: true },
  ];
  return (
    <Sl visible={v}>
      <Orb color={C.accent} size={250} top={0} left={-80} opacity={0.06} />
      <SH badge="Tagging Matrix" bc={C.warn} title="What Tags" hl="Actually Control" hc={C.warn} sub="TBAC covers operational resources but misses where tenant data lives" />
      <div style={{ maxWidth: 600, margin: "0 auto", position: "relative", zIndex: 1 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 80px 80px", padding: "8px 14px", borderRadius: "10px 10px 0 0", background: C.surfaceLight, borderBottom: `1px solid ${C.border}` }}>
          {["Resource", "Taggable", "TBAC"].map(h => <span key={h} style={{ fontSize: 10, fontWeight: 700, color: C.textDim, textTransform: "uppercase", letterSpacing: 1, textAlign: h === "Resource" ? "left" : "center", fontFamily: F }}>{h}</span>)}
        </div>
        {res.map((r, i) => (
          <div key={r.n} style={{ display: "grid", gridTemplateColumns: "1fr 80px 80px", padding: "7px 14px", borderBottom: `1px solid ${C.border}`, background: r.c ? `${C.danger}06` : "transparent" }}>
            <span style={{ fontSize: 12, color: r.c ? C.danger : C.text, fontWeight: r.c ? 600 : 400, display: "flex", alignItems: "center", gap: 5, fontFamily: F }}>{r.c && <span style={{ fontSize: 9 }}>🚨</span>}{r.n}</span>
            <span style={{ textAlign: "center", fontSize: 14 }}>{r.tg ? "✅" : "❌"}</span>
            <span style={{ textAlign: "center", fontSize: 14 }}>{r.tb === true ? "✅" : r.tb === "p" ? "⚠️" : "❌"}</span>
          </div>
        ))}
        <div style={{ marginTop: 14, padding: "12px 16px", borderRadius: 10, background: `linear-gradient(135deg, ${C.dangerDim}, ${C.warnDim})`, border: `1px solid ${C.danger}33` }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: C.danger, marginBottom: 4, fontFamily: F }}>The Critical Gap</div>
          <div style={{ fontSize: 11, color: C.textDim, lineHeight: 1.6, fontFamily: F }}><strong style={{ color: C.text }}>Contacts cannot be tagged.</strong> S3 recordings land in shared buckets. Contact Lens dashboards ignore TBAC. One misconfigured security profile exposes all tenants' data.</div>
        </div>
      </div>
    </Sl>
  );
}

// 4. DOMAIN LOCKS
function S4({ v }) {
  const d = [
    { n: "Customer Profiles", i: "👤", co: C.accent, cn: "1 domain / instance", im: "All tenant PII pools into one domain. Identity Resolution merges duplicates across tenants. No TBAC on profile data." },
    { n: "Amazon Connect Cases", i: "📁", co: C.warn, cn: "1 Cases domain / instance", im: "All case templates, fields, layouts shared. DWP benefits cases and NHS safeguarding cases in the same domain." },
    { n: "Amazon Q in Connect", i: "🧠", co: C.success, cn: "1 AI agent domain / instance", im: "One knowledge base feeds all agents. HMRC tax guidance and NHS clinical pathways cannot be separated." },
    { n: "Outbound Campaigns", i: "📞", co: C.purple, cn: "Instance + account quotas", im: "Campaign management and predictive dialer shared. One tenant's burst exhausts quotas for all." },
    { n: "Evaluation Forms", i: "📝", co: C.rose, cn: "Instance-wide", im: "Performance evaluations shared. Supervisors see all agents' evaluations. Gen AI auto-evals process all contacts." },
    { n: "Agent Scheduling", i: "📅", co: "#38bdf8", cn: "Instance-level", im: "Scheduling rules, shift profiles, staffing forecasts at instance level. Cross-tenant pools break forecasting." },
  ];
  return (
    <Sl visible={v}>
      <Orb color={C.rose} size={350} top={-80} left="40%" opacity={0.06} />
      <SH badge="1:1 Domain Locks" bc={C.rose} title="One Instance =" hl="One Domain Each" hc={C.rose} sub="Six critical services hard-locked to a single domain per instance — no tenant partitioning" />
      <div style={{ maxWidth: 680, margin: "0 auto", position: "relative", zIndex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginBottom: 18, padding: "10px 16px", borderRadius: 12, background: `${C.rose}08`, border: `1px solid ${C.rose}22` }}>
          <span style={{ fontSize: 20 }}>🔒</span><span style={{ fontSize: 11, color: C.rose, fontWeight: 700, fontFamily: F, letterSpacing: 0.4 }}>1 INSTANCE = 1 Profiles Domain = 1 Cases Domain = 1 Q Domain = 1 Scheduling Domain</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(290px, 1fr))", gap: 10 }}>
          {d.map((x, i) => (
            <div key={x.n} style={{ padding: "14px", borderRadius: 12, border: `1px solid ${x.co}33`, background: `linear-gradient(160deg, ${x.co}06, ${C.surface})` }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}><span style={{ fontSize: 18 }}>{x.i}</span><div><div style={{ fontSize: 12, fontWeight: 700, color: x.co, fontFamily: F }}>{x.n}</div><div style={{ fontSize: 8, fontWeight: 700, color: C.danger, letterSpacing: 0.5, textTransform: "uppercase", fontFamily: F, marginTop: 1, padding: "1px 5px", borderRadius: 3, background: `${C.danger}12`, display: "inline-block" }}>{x.cn}</div></div></div>
              <p style={{ fontSize: 10, color: C.textDim, lineHeight: 1.55, margin: 0, fontFamily: F }}>{x.im}</p>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 14, padding: "12px 16px", borderRadius: 10, background: `linear-gradient(135deg, ${C.roseDim}, ${C.dangerDim})`, border: `1px solid ${C.rose}33`, textAlign: "center" }}>
          <div style={{ fontSize: 11, color: C.textDim, lineHeight: 1.6, fontFamily: F }}>Each domain is a <strong style={{ color: C.text }}>single flat namespace</strong>. NHS patient profiles, HMRC taxpayer records, DWP benefits cases, and Home Office immigration data all inhabit the same container.</div>
        </div>
      </div>
    </Sl>
  );
}

// 5. GAPS
function S5({ v }) {
  const g = [
    { t: "Security Profile Override", co: C.danger, i: "🔓", d: "Any admin with an unrestricted security profile bypasses all TBAC. One misconfiguration exposes every tenant.", tg: "NCSC Principle 3" },
    { t: "Contact Search Leakage", co: C.warn, i: "🔎", d: "Contact Search returns cross-tenant results. NHS supervisor could surface HMRC conversations.", tg: "FOIA cross-contamination" },
    { t: "S3 Race Condition", co: C.purple, i: "⏱️", d: "Lambda pipeline must move recordings instantly. Any failure leaves data in shared bucket.", tg: "Data minimisation breach" },
    { t: "Kinesis / CloudWatch", co: C.accent, i: "📡", d: "CTRs into shared Kinesis. CloudWatch logs all tenants. No tag-based filtering.", tg: "No tenant isolation" },
  ];
  return (
    <Sl visible={v}>
      <Orb color={C.danger} size={350} top={-80} left="50%" opacity={0.05} />
      <SH badge="Failure Modes" bc={C.danger} title="Where" hl="Isolation Fails" hc={C.danger} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(270px, 1fr))", gap: 12, maxWidth: 660, margin: "0 auto", position: "relative", zIndex: 1 }}>
        {g.map((x, i) => (
          <div key={x.t} style={{ padding: "18px", borderRadius: 14, border: `1px solid ${x.co}33`, background: `linear-gradient(160deg, ${x.co}08, ${C.surface})` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}><span style={{ fontSize: 22 }}>{x.i}</span><span style={{ fontSize: 13, fontWeight: 700, color: x.co, fontFamily: F }}>{x.t}</span></div>
            <p style={{ fontSize: 11, color: C.textDim, lineHeight: 1.6, margin: 0, fontFamily: F }}>{x.d}</p>
            <div style={{ marginTop: 10, padding: "4px 8px", borderRadius: 6, background: `${x.co}10`, border: `1px solid ${x.co}22`, fontSize: 9, fontWeight: 700, color: x.co, letterSpacing: 0.5, textTransform: "uppercase", fontFamily: F }}>{x.tg}</div>
          </div>
        ))}
      </div>
    </Sl>
  );
}

// 6. AI BUNDLE
function S6({ v }) {
  return (
    <Sl visible={v}>
      <Orb color={C.warn} size={300} top={-60} left="30%" opacity={0.06} />
      <SH badge="Cost Architecture" bc={C.warn} title="The" hl="Unlimited AI Trap" hc={C.warn} sub="Instance-level toggle with no per-tenant granularity" />
      <div style={{ maxWidth: 580, margin: "0 auto", position: "relative", zIndex: 1 }}>
        <div style={{ display: "flex", gap: 14, justifyContent: "center", marginBottom: 20, flexWrap: "wrap" }}>
          {[{ on: true, l: "✅ AI Enabled", p: "$0.038", note: "ALL tenants pay — even those not using AI", nc: C.warn, b: C.success, bg: C.successDim },
            { on: false, l: "❌ AI Disabled", p: "$0.018", note: "NO tenants get AI — even those that need it", nc: C.danger, b: C.textDim, bg: C.surface }
          ].map(s => (
            <div key={s.l} style={{ flex: 1, minWidth: 230, padding: 18, borderRadius: 14, border: `1px solid ${s.b}33`, background: s.bg }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: s.on ? C.success : C.textDim, marginBottom: 6, textTransform: "uppercase", letterSpacing: 1, fontFamily: F }}>{s.l}</div>
              <div style={{ fontSize: 26, fontWeight: 800, color: s.on ? C.text : C.textDim, fontFamily: F }}>{s.p}<span style={{ fontSize: 13, color: C.textDim }}>/min</span></div>
              <div style={{ fontSize: 10, color: s.on ? C.textDim : `${C.textDim}88`, marginTop: 5, lineHeight: 1.5, textDecoration: s.on ? "none" : "line-through", fontFamily: F }}>Contact Lens · Q in Connect · Perf Eval · Screen Rec · Scheduling · AI Lex</div>
              <div style={{ display: "flex", gap: 3, marginTop: 8, flexWrap: "wrap" }}>
                {T.map(t => <span key={t.name} style={{ padding: "1px 6px", borderRadius: 3, background: s.on ? `${t.color}22` : `${C.textDim}11`, color: s.on ? t.color : `${C.textDim}88`, fontSize: 9, fontWeight: 700, fontFamily: F }}>{t.name}</span>)}
              </div>
              <div style={{ fontSize: 9, color: s.nc, marginTop: 6, fontWeight: 600, fontFamily: F }}>{s.note}</div>
            </div>
          ))}
        </div>
        <div style={{ padding: "14px 18px", borderRadius: 12, background: `linear-gradient(135deg, ${C.warnDim}, ${C.dangerDim})`, border: `1px solid ${C.warn}33`, textAlign: "center" }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: C.warn, marginBottom: 4, fontFamily: F }}>The Unanimous-Consent Problem</div>
          <div style={{ fontSize: 11, color: C.textDim, lineHeight: 1.6, fontFamily: F }}>NHS needs Contact Lens for <strong style={{ color: C.success }}>safeguarding keyword detection</strong>. DWP refuses the higher rate. <strong style={{ color: C.danger }}>Neither gets what they need.</strong></div>
        </div>
      </div>
    </Sl>
  );
}

// 7. TECHNICAL
function S7({ v }) {
  const m = [
    { n: "Bootstrap Flows + DynamoDB Config", w: "Centralized IVR routing with per-tenant config lookup via DynamoDB.", s: "valid", vd: "Addresses routing only. No data isolation.", co: C.success },
    { n: "TBAC on Agents, Queues, Routing Profiles", w: "Tag resources with tenant identifier. Security profiles restrict by access control tags.", s: "partial", vd: "Works for operational resources. Does NOT cover Contacts, S3, Contact Lens, Kinesis, CloudWatch, Profiles, Cases, or Q.", co: C.warn },
    { n: "KMS + S3 Lambda Pipeline", w: "Per-tenant KMS keys. Lambda on S3 PutObject moves recordings to tenant-specific buckets.", s: "fragile", vd: "Race condition: data in shared bucket until Lambda completes. Any failure leaves data exposed.", co: C.warn },
    { n: "Athena CTR Billing", w: "Query CTRs in Athena, filter by queue/tenant, generate per-tenant cost reports.", s: "partial", vd: "CTR costs only (50-70%). Cannot track Lambda, DynamoDB, Kinesis, Lex, S3, KMS, or CloudWatch.", co: C.warn },
    { n: "Managed-Access Model", w: "Tenants never access Connect UI. Maximus operates instance, exports reports.", s: "best", vd: "Most defensible. But loses native supervisor capabilities. Months to replicate. Does not achieve NCSC Principle 3.", co: C.accent },
    { n: "Hierarchy-Based Access Control", w: "Assign agents to hierarchy groups per tenant. Restrict contact access by hierarchy.", s: "partial", vd: "Only restricts by which agent handled the contact. No effect on S3, Kinesis, or domain-locked services.", co: C.warn },
  ];
  const sm = { valid: { l: "Works", c: C.success }, partial: { l: "Partial", c: C.warn }, fragile: { l: "Fragile", c: C.danger }, best: { l: "Best Option", c: C.accent } };
  const lim = [
    "Contacts are not taggable — the fundamental resource has no access control",
    "Contact Lens dashboards explicitly do not support TBAC",
    "Customer Profiles, Cases, Q, Scheduling: 1 domain per instance, no sub-tenancy",
    "Security profile misconfiguration is a single point of failure for all tenants",
    "S3 recordings have no native tenant partition; requires custom Lambda pipeline",
    "Outbound campaign quotas are per-account, not per-tenant",
    "Unlimited AI pricing is instance-wide binary toggle",
    "No native per-tenant billing; custom Athena pipeline with incomplete cost coverage",
  ];
  return (
    <Sl visible={v}>
      <Orb color={C.teal} size={350} top={-60} left="20%" opacity={0.06} />
      <SH badge="Technical Solution Path" bc={C.teal} title="If You Must" hl="Share an Instance" hc={C.teal} sub="Every mitigation, its coverage, and what it leaves exposed" />
      <div style={{ maxWidth: 700, margin: "0 auto", position: "relative", zIndex: 1 }}>
        {m.map((x, i) => { const st = sm[x.s]; return (
          <div key={x.n} style={{ marginBottom: 10, padding: "14px 16px", borderRadius: 12, border: `1px solid ${x.co}22`, background: `${x.co}04` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 9, fontWeight: 700, color: st.c, background: `${st.c}18`, border: `1px solid ${st.c}33`, textTransform: "uppercase", letterSpacing: 0.5, fontFamily: F }}>{st.l}</span>
              <span style={{ fontSize: 13, fontWeight: 700, color: C.text, fontFamily: F }}>{x.n}</span>
            </div>
            <div style={{ fontSize: 11, color: C.textDim, lineHeight: 1.5, marginBottom: 6, fontFamily: F }}>{x.w}</div>
            <div style={{ fontSize: 11, color: x.co, lineHeight: 1.5, fontWeight: 600, fontFamily: F, padding: "6px 10px", borderRadius: 6, background: `${x.co}08` }}>→ {x.vd}</div>
          </div>
        ); })}
        <div style={{ marginTop: 18, padding: "16px 18px", borderRadius: 12, border: `1px solid ${C.danger}33`, background: `${C.danger}06` }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: C.danger, marginBottom: 10, fontFamily: F }}>⛔ Hard Platform Limitations (Cannot Be Mitigated)</div>
          {lim.map((l, i) => (<div key={i} style={{ display: "flex", gap: 8, marginBottom: 6, fontSize: 11, color: C.textDim, lineHeight: 1.5, fontFamily: F }}><span style={{ color: C.danger, fontWeight: 700, flexShrink: 0 }}>✕</span><span>{l}</span></div>))}
        </div>
      </div>
    </Sl>
  );
}

// 8. BUSINESS DECISION
function S8({ v }) {
  const [tab, setTab] = useState("compare");
  const pros = [
    { t: "Lower Initial Setup", d: "One instance to configure, one set of flows, one deployment pipeline. Faster time-to-first-tenant.", i: "🚀" },
    { t: "Shared Agent Pool", d: "Cross-trained agents serve multiple tenants. Higher utilization during low-volume periods.", i: "👥" },
    { t: "Centralized Operations", d: "Single pane of glass for monitoring. One team manages all tenants.", i: "🖥️" },
    { t: "Reusable Flow Library", d: "Bootstrap flows, IVR templates, Lex bots shared. Build once, deploy many.", i: "🔄" },
    { t: "Potential Volume Discounts", d: "Aggregated usage may qualify for AWS Enterprise Discount Program.", i: "📉" },
  ];
  const cons = [
    { t: "UK GDPR Liability", d: "Joint controllership or processor confusion. ICO fines up to £17.5M or 4% turnover.", i: "⚖️", s: "critical" },
    { t: "FOIA Cross-Contamination", d: "Broad FOI request to one agency could sweep another's data. Disclosures are \"to the world.\"", i: "📜", s: "critical" },
    { t: "NCSC Non-Compliance", d: "No technically enforced separation between consumers of the service.", i: "🛡️", s: "critical" },
    { t: "Blocked AI Adoption", d: "Instance-level toggle: one objecting tenant blocks AI for everyone.", i: "🧠", s: "high" },
    { t: "No Native Supervision", d: "Managed-access loses silent monitor, barge, whisper. Months to replicate.", i: "👁️", s: "high" },
    { t: "Domain Lock-In", d: "Profiles, Cases, Q, Scheduling — one domain per instance. PII commingled.", i: "🔒", s: "critical" },
    { t: "Delivery Velocity Risk", d: "Each new tenant requires TBAC validation, S3 pipeline confirmation, cross-tenant testing.", i: "🐌", s: "medium" },
    { t: "Billing Complexity", d: "Custom Athena covers only CTR costs (50-70%). Lambda/DynamoDB/Kinesis unattributable.", i: "💸", s: "medium" },
    { t: "Single Point of Failure", d: "One misconfigured security profile exposes all tenants simultaneously.", i: "💥", s: "high" },
    { t: "Audit Burden", d: "Shared instance makes DSPT scoping and DPIA assessments exponentially harder.", i: "📋", s: "high" },
  ];
  const sc = [
    { t: "Multi-Tenant Works Well", co: C.success, i: "✅", items: ["Single legal entity (multiple brands/divisions)", "Commercial tenants accepting residual risk via contract", "Maximus internal operations (single controller)", "All tenants agree on AI enablement and pricing model", "Tenants share agent pools, don't need separate supervision"] },
    { t: "Multi-Tenant is Dangerous", co: C.danger, i: "⛔", items: ["Independent UK government entities (separate data controllers)", "NHS trusts handling patient data (DSPT requirements)", "Tenants with different AI/budget requirements", "Agencies subject to different FOI jurisdictions", "Devolved administrations (Scotland, NI, own frameworks)"] },
  ];
  const sev = { critical: C.danger, high: C.warn, medium: C.slate };
  return (
    <Sl visible={v}>
      <Orb color={C.purple} size={350} top={-80} left="30%" opacity={0.06} />
      <SH badge="Business Decision" bc={C.purple} title="Should We" hl="Share an Instance?" hc={C.purple} sub="A balanced view for business owners to weigh operational efficiency against risk" />
      <div style={{ maxWidth: 700, margin: "0 auto", position: "relative", zIndex: 1 }}>
        <div style={{ display: "flex", gap: 6, justifyContent: "center", marginBottom: 20 }}>
          {[{ id: "compare", l: "Pros vs. Cons" }, { id: "scenarios", l: "When It Works vs. Doesn't" }].map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} style={{ padding: "7px 18px", borderRadius: 10, border: "none", cursor: "pointer", fontSize: 12, fontWeight: 600, fontFamily: F, transition: "all 0.2s", background: tab === t.id ? `${C.purple}22` : C.surface, color: tab === t.id ? C.purple : C.textDim, outline: tab === t.id ? `1px solid ${C.purple}44` : `1px solid ${C.borderLight}` }}>{t.l}</button>
          ))}
        </div>
        {tab === "compare" && (<div>
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}><span style={{ fontSize: 16 }}>👍</span><span style={{ fontSize: 14, fontWeight: 700, color: C.success, fontFamily: F }}>Arguments FOR Multi-Tenancy</span></div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 8 }}>
              {pros.map((p, i) => (<div key={p.t} style={{ padding: "12px 14px", borderRadius: 10, border: `1px solid ${C.success}22`, background: `${C.success}04` }}><div style={{ fontSize: 16, marginBottom: 4 }}>{p.i}</div><div style={{ fontSize: 11, fontWeight: 700, color: C.success, marginBottom: 3, fontFamily: F }}>{p.t}</div><div style={{ fontSize: 10, color: C.textDim, lineHeight: 1.5, fontFamily: F }}>{p.d}</div></div>))}
            </div>
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}><span style={{ fontSize: 16 }}>👎</span><span style={{ fontSize: 14, fontWeight: 700, color: C.danger, fontFamily: F }}>Arguments AGAINST (Sovereign Government Context)</span></div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 8 }}>
              {cons.map((c, i) => (<div key={c.t} style={{ padding: "12px 14px", borderRadius: 10, border: `1px solid ${sev[c.s]}22`, background: `${sev[c.s]}04` }}><div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}><span style={{ fontSize: 14 }}>{c.i}</span><span style={{ padding: "1px 5px", borderRadius: 3, fontSize: 8, fontWeight: 700, color: sev[c.s], background: `${sev[c.s]}18`, textTransform: "uppercase", letterSpacing: 0.5, fontFamily: F }}>{c.s}</span></div><div style={{ fontSize: 11, fontWeight: 700, color: sev[c.s], marginBottom: 3, fontFamily: F }}>{c.t}</div><div style={{ fontSize: 10, color: C.textDim, lineHeight: 1.5, fontFamily: F }}>{c.d}</div></div>))}
            </div>
          </div>
          <div style={{ marginTop: 16, padding: "14px 18px", borderRadius: 10, background: `linear-gradient(135deg, ${C.purpleDim}, ${C.dangerDim})`, border: `1px solid ${C.purple}33`, textAlign: "center" }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: C.purple, marginBottom: 4, fontFamily: F }}>The Core Question</div>
            <div style={{ fontSize: 12, color: C.textDim, lineHeight: 1.7, fontFamily: F }}>Do <strong style={{ color: C.success }}>5 operational conveniences</strong> outweigh <strong style={{ color: C.danger }}>10 risks</strong> — including 4 rated <strong style={{ color: C.danger }}>critical</strong> under enforceable UK law? The benefits can be replicated via IaC. The regulatory risks <strong style={{ color: C.text }}>cannot be engineered away</strong>.</div>
          </div>
        </div>)}
        {tab === "scenarios" && (<div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 14 }}>
            {sc.map((s, si) => (<div key={s.t} style={{ padding: "18px", borderRadius: 14, border: `1px solid ${s.co}33`, background: `${s.co}06` }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}><span style={{ fontSize: 22 }}>{s.i}</span><span style={{ fontSize: 14, fontWeight: 700, color: s.co, fontFamily: F }}>{s.t}</span></div>
              {s.items.map((item, i) => (<div key={i} style={{ display: "flex", gap: 8, marginBottom: 8, fontSize: 12, color: C.textDim, lineHeight: 1.5, fontFamily: F }}><span style={{ color: s.co, fontWeight: 700, flexShrink: 0, fontSize: 10, marginTop: 2 }}>●</span><span>{item}</span></div>))}
            </div>))}
          </div>
          <div style={{ marginTop: 18, padding: "16px 20px", borderRadius: 12, border: `1px solid ${C.accent}33`, background: `${C.accent}06`, textAlign: "center" }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: C.accent, marginBottom: 6, fontFamily: F }}>The Boundary Is Sovereignty</div>
            <div style={{ fontSize: 12, color: C.textDim, lineHeight: 1.7, fontFamily: F }}>Multi-tenancy works <strong style={{ color: C.success }}>within a single data controller</strong>. It fails where tenants are <strong style={{ color: C.danger }}>independent controllers with independent legal obligations</strong>.</div>
          </div>
        </div>)}
      </div>
    </Sl>
  );
}

// 9. FAQ (NEW)
function S9({ v }) {
  const [open, setOpen] = useState(null);
  const faqs = [
    {
      q: "Doesn't Tag-Based Access Control (TBAC) solve multi-tenant isolation?",
      a: "TBAC controls access to operational resources like agents, queues, and routing profiles. However, the most critical resource — the Contact itself — cannot be tagged. S3 recordings, Kinesis streams, and CloudWatch logs have no TBAC support. The Contact Lens dashboard explicitly does not support tag-based access controls. TBAC is a visibility filter on the admin UI, not a data-layer isolation boundary.",
      sources: [
        { label: "AWS: Add tags to resources (Contact = No)", url: "https://docs.aws.amazon.com/connect/latest/adminguide/tagging.html" },
        { label: "AWS: Tag-based access control (override risk)", url: "https://docs.aws.amazon.com/connect/latest/adminguide/tag-based-access-control.html" },
        { label: "AWS: Contact Lens dashboard (TBAC not supported)", url: "https://docs.aws.amazon.com/connect/latest/adminguide/contact-lens-conversational-analytics-dashboard.html" },
      ],
      color: C.warn,
    },
    {
      q: "Is there a per-instance fee that makes separate instances more expensive?",
      a: "No. Amazon Connect pricing is purely consumption-based. There are no per-instance fees, no minimum monthly commitments, and no upfront license charges. You pay only for what you use: per-minute for voice, per-message for chat, and per-use for individual features. Running four instances at 25% volume each costs the same as one instance at 100% volume. On G-Cloud, each agency requires its own call-off contract regardless of instance architecture.",
      sources: [
        { label: "AWS: Amazon Connect Pricing", url: "https://aws.amazon.com/connect/pricing/" },
        { label: "AWS: G-Cloud UK (individual call-off contracts)", url: "https://aws.amazon.com/government-education/g-cloud-uk/" },
      ],
      color: C.success,
    },
    {
      q: "Can Customer Profiles be isolated per tenant on a shared instance?",
      a: "No. Each Amazon Connect instance can only be associated with one Customer Profiles domain. All customer profile data — names, addresses, phone numbers, contact history — pools into that single domain. Identity Resolution will actively merge profiles that look similar across tenants. There is no TBAC, no sub-domain, and no per-tenant partition within a Profiles domain. An agent with Profiles permission can search and view any profile.",
      sources: [
        { label: "AWS: Enable Customer Profiles (1 domain per instance)", url: "https://docs.aws.amazon.com/connect/latest/adminguide/enable-customer-profiles.html" },
      ],
      color: C.accent,
    },
    {
      q: "Can Amazon Q knowledge bases be scoped per tenant?",
      a: "No. Each Connect instance can only be associated with one Amazon Q (AI agent) domain, which contains one knowledge base. All agents on the instance receive recommendations from the same knowledge base. HMRC tax procedures and NHS clinical pathways cannot be separated. Guardrails, prompt tuning, and content ingestion all apply instance-wide.",
      sources: [
        { label: "AWS: Initial setup for AI agents (1 domain per instance)", url: "https://docs.aws.amazon.com/connect/latest/adminguide/ai-agent-initial-setup.html" },
        { label: "AWS re:Post: Amazon Q domain limit confirmed", url: "https://repost.aws/questions/QUs9juBdqNRd2iswbDzBbkXQ/amazon-connect-wisdom-amazon-q" },
      ],
      color: C.success,
    },
    {
      q: "Can we enable Contact Lens AI for one tenant but not another?",
      a: "No. The Unlimited AI pricing toggle (formerly \"Next Generation Amazon Connect\") is an instance-level binary switch. When enabled, all traffic on the instance is billed at the AI-inclusive rate ($0.038/min voice). When disabled, no tenant gets Contact Lens, Q in Connect, performance evaluation, screen recording, or agent scheduling. There is no per-queue, per-tenant, or per-flow granularity.",
      sources: [
        { label: "AWS: Enable/Disable Unlimited AI Pricing (instance toggle)", url: "https://docs.aws.amazon.com/connect/latest/adminguide/enable-nextgeneration-amazonconnect.html" },
        { label: "AWS: Amazon Connect Pricing (Unlimited AI model)", url: "https://aws.amazon.com/connect/pricing/" },
      ],
      color: C.warn,
    },
    {
      q: "Does NCSC require hard separation between tenants?",
      a: "Yes. NCSC Cloud Security Principle 3 (Separation Between Consumers) requires that a malicious or compromised consumer of the service cannot affect the service or data of another. The guidance specifies that the separation should be technically enforced, not dependent on operational controls alone. Application-layer tag controls that can be overridden by a single misconfigured security profile do not meet this standard.",
      sources: [
        { label: "NCSC: Cloud Security Principles (Principle 3)", url: "https://www.ncsc.gov.uk/collection/cloud/the-cloud-security-principles" },
        { label: "NCSC: Summary of Cloud Security Principles (PDF)", url: "https://assets.publishing.service.gov.uk/media/5a7d7abfed915d269ba8aea2/Summary_of_Cloud_Security_Principles.pdf" },
      ],
      color: C.danger,
    },
    {
      q: "What does UK GDPR say about multiple government entities sharing a platform?",
      a: "Each UK government entity is a separate data controller under UK GDPR. Sharing an instance creates either inadvertent joint controllership under Article 26 (requiring a formal arrangement with mutual liability) or controller-processor confusion under Article 28. The ICO's Data Sharing Code (statutory force under DPA 2018) requires a DPIA when data from multiple sources is combined. ICO fines can reach £17.5M or 4% of annual turnover.",
      sources: [
        { label: "ICO: Controllers and processors", url: "https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/controllers-and-processors/controllers-and-processors/what-are-controllers-and-processors/" },
        { label: "ICO: Data sharing code of practice", url: "https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/data-sharing/data-sharing-a-code-of-practice/" },
        { label: "ICO: Data Protection Impact Assessments", url: "https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/data-protection-impact-assessments-dpias/" },
      ],
      color: C.danger,
    },
    {
      q: "What happens if one agency receives a Freedom of Information request?",
      a: "FOIA 2000 applies to all UK public authorities, covering any recorded information held. Disclosures under FOIA are \"to the world.\" Shared infrastructure means a broad FOI request to one agency could sweep metadata, dashboards, operational reports, or contact records that include data belonging to another agency. Scotland operates under separate FOI legislation with its own Information Commissioner, adding jurisdictional complexity.",
      sources: [
        { label: "ICO: FOI Act coverage", url: "https://ico.org.uk/for-organisations/foi/what-is-the-foi-act-and-are-we-covered/" },
        { label: "UK Legislation: FOIA 2000 (full text)", url: "https://www.legislation.gov.uk/ukpga/2000/36/pdfs/ukpgaod_20000036_en.pdf" },
      ],
      color: C.rose,
    },
    {
      q: "Does AWS itself recommend account-per-tenant for multi-tenant SaaS?",
      a: "Yes. The AWS Architecture Blog describes account-per-tenant as providing \"a hard security boundary where the account itself becomes the isolation boundary.\" It explicitly notes that shared-account models \"require resource-level controls that increase complexity and introduce security challenges.\" AWS Organizations enables shared billing and centralized governance across per-tenant accounts.",
      sources: [
        { label: "AWS Architecture Blog: Account-per-tenant (6000 accounts, 3 people)", url: "https://aws.amazon.com/blogs/architecture/6000-aws-accounts-three-people-one-platform-lessons-learned/" },
      ],
      color: C.accent,
    },
    {
      q: "What about NHS DSPT requirements?",
      a: "Any organisation accessing NHS patient data must annually complete the Data Security and Protection Toolkit (DSPT). The DSPT requires that personal confidential data is only accessible to staff who need it, and that all access is individually attributable. A shared multi-tenant instance makes scoping the DSPT assessment significantly harder because the boundary of \"the system\" includes other tenants' data and agents. Each NHS trust needs its own DSPT submission.",
      sources: [
        { label: "NHS England: Data Security and Protection Toolkit", url: "https://www.dsptoolkit.nhs.uk/" },
        { label: "AWS: NHS DSPT compliance", url: "https://aws.amazon.com/compliance/nhs-dspt/" },
      ],
      color: C.success,
    },
    {
      q: "Can Cases be isolated per tenant with tag-based access?",
      a: "Partially. Cases can inherit tags from their templates, and TBAC can restrict case visibility based on those tags. However, each instance can only have one Cases domain, meaning all case field definitions, layouts, and templates are shared across tenants. The tag inheritance helps with case-level visibility but does not partition the domain's schema or configuration. A misconfigured template could expose cross-tenant cases.",
      sources: [
        { label: "AWS: Cases domain (1 per instance)", url: "https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-cases-domain.html" },
        { label: "AWS: Set up tag-based access controls on Cases", url: "https://docs.aws.amazon.com/connect/latest/adminguide/cases-tag-based-access-control.html" },
      ],
      color: C.warn,
    },
    {
      q: "What supervisor capabilities are lost under the managed-access model?",
      a: "All native live interaction monitoring is lost. Amazon Connect's silent monitoring, barge-in, and whisper coaching are built entirely into the Connect admin website and CCP. There is no external API for live call monitoring. Supervisors cannot listen to live calls, join calls to intervene, coach agents in real time, or view live agent state / queue metrics. Replicating these requires Kinesis Video Streams, custom WebSocket interfaces, Connect Streams API, agent event stream processing, and custom real-time dashboards with per-tenant authentication — months of development.",
      sources: [
        { label: "AWS: Assign permissions to review conversations", url: "https://docs.aws.amazon.com/connect/latest/adminguide/assign-permissions-to-review-recordings.html" },
        { label: "AWS: Security profile permissions list", url: "https://docs.aws.amazon.com/connect/latest/adminguide/security-profile-list.html" },
      ],
      color: C.purple,
    },
  ];

  return (
    <Sl visible={v}>
      <Orb color={C.amber} size={350} top={-80} left="25%" opacity={0.06} />
      <Orb color={C.accent} size={250} top={700} left="65%" opacity={0.04} />
      <SH badge="Frequently Asked Questions" bc={C.amber} title="Questions" hl="& Answers" hc={C.amber} sub="Click any question to expand. All answers include citations with links to authoritative sources." />
      <div style={{ maxWidth: 700, margin: "0 auto", position: "relative", zIndex: 1 }}>
        {faqs.map((faq, i) => {
          const isOpen = open === i;
          return (
            <div key={i} style={{
              marginBottom: 8, borderRadius: 12, border: `1px solid ${isOpen ? faq.color + "44" : C.borderLight}`,
              background: isOpen ? `${faq.color}06` : C.surface, transition: "all 0.3s",
              animation: `fadeUp 0.3s ease ${i * 0.04}s both`, overflow: "hidden",
            }}>
              <button onClick={() => setOpen(isOpen ? null : i)} style={{
                width: "100%", padding: "14px 16px", border: "none", cursor: "pointer",
                background: "transparent", display: "flex", alignItems: "flex-start", gap: 10, textAlign: "left",
              }}>
                <span style={{
                  width: 22, height: 22, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center",
                  background: `${faq.color}18`, color: faq.color, fontSize: 12, fontWeight: 700, flexShrink: 0, marginTop: 1,
                  transition: "transform 0.3s", transform: isOpen ? "rotate(45deg)" : "rotate(0deg)",
                }}>+</span>
                <span style={{ fontSize: 13, fontWeight: 600, color: isOpen ? faq.color : C.text, lineHeight: 1.4, fontFamily: F }}>{faq.q}</span>
              </button>
              {isOpen && (
                <div style={{ padding: "0 16px 16px 48px" }}>
                  <p style={{ fontSize: 12, color: C.textDim, lineHeight: 1.7, margin: "0 0 12px", fontFamily: F }}>{faq.a}</p>
                  <div style={{ padding: "10px 12px", borderRadius: 8, background: `${faq.color}08`, border: `1px solid ${faq.color}18` }}>
                    <div style={{ fontSize: 9, fontWeight: 700, color: faq.color, textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 6, fontFamily: F }}>Sources</div>
                    {faq.sources.map((src, si) => (
                      <div key={si} style={{ marginBottom: si < faq.sources.length - 1 ? 6 : 0 }}>
                        <a href={src.url} target="_blank" rel="noopener noreferrer" style={{
                          fontSize: 11, color: faq.color, textDecoration: "none", fontFamily: F,
                          display: "flex", alignItems: "flex-start", gap: 6, lineHeight: 1.4,
                        }}>
                          <span style={{ flexShrink: 0, marginTop: 2 }}>🔗</span>
                          <span style={{ borderBottom: `1px solid ${faq.color}33` }}>{src.label}</span>
                        </a>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Sl>
  );
}

// 10. SOLUTION
function S10({ v }) {
  return (
    <Sl visible={v}>
      <Orb color={C.success} size={400} top={-100} left="20%" opacity={0.05} />
      <Orb color={C.accent} size={300} top={350} left="70%" opacity={0.04} />
      <SH badge="Recommended Architecture" bc={C.success} title="Per-Agency" hl="Instances" hc={C.success} sub="Separate AWS accounts per entity — same cost, hard boundaries, independent domains" />
      <div style={{ maxWidth: 700, margin: "0 auto", position: "relative", zIndex: 1 }}>
        <div style={{ padding: "10px 18px", borderRadius: "12px 12px 0 0", background: `${C.accent}10`, border: `1px solid ${C.accent}22`, borderBottom: "none", textAlign: "center" }}>
          <span style={{ fontSize: 10, fontWeight: 700, color: C.accent, letterSpacing: 1, textTransform: "uppercase", fontFamily: F }}>AWS Organization — Shared Billing · Monitoring · IaC Templates · Deployment Automation</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(148px, 1fr))", gap: 10, padding: 14, border: `1px solid ${C.accent}22`, borderRadius: "0 0 12px 12px", background: C.surface }}>
          {T.map((t, i) => (
            <div key={t.name} style={{ padding: 12, borderRadius: 12, border: `1px solid ${t.color}33`, background: `${t.color}06` }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
                <span style={{ width: 26, height: 26, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center", background: `${t.color}22`, color: t.color, fontSize: 13, fontWeight: 700 }}>{t.icon}</span>
                <span style={{ fontSize: 11, fontWeight: 700, color: t.color, fontFamily: F }}>{t.name}</span>
              </div>
              {["Own AWS Account", "Own Connect Instance", "Own Profiles Domain", "Own Cases Domain", "Own Q Knowledge Base", "Own Outbound Campaigns", "Own S3 / KMS / Kinesis", "Own DSPT / DPIA", "AI: Independent toggle"].map(item => (
                <div key={item} style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 2, fontSize: 9, color: C.textDim, fontFamily: F }}>
                  <span style={{ width: 3, height: 3, borderRadius: 1, background: t.color, opacity: 0.7, flexShrink: 0 }} />{item}
                </div>
              ))}
              <div style={{ marginTop: 8, padding: "3px 6px", borderRadius: 4, background: `${C.success}12`, border: `1px solid ${C.success}22`, fontSize: 8, fontWeight: 700, color: C.success, textTransform: "uppercase", letterSpacing: 0.5, textAlign: "center", fontFamily: F }}>Hard boundary</div>
            </div>
          ))}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(155px, 1fr))", gap: 8, marginTop: 14 }}>
          {[
            { l: "Same Cost", d: "Consumption pricing, no per-instance fee", i: "💰", co: C.success },
            { l: "Separate Domains", d: "Profiles, Cases, Q — each agency owns data", i: "🔐", co: C.rose },
            { l: "Full AI Freedom", d: "Each agency enables AI independently", i: "🧠", co: C.accent },
            { l: "Native Supervision", d: "Silent monitor, barge, whisper — native", i: "👁️", co: C.purple },
          ].map((b, i) => (
            <div key={b.l} style={{ padding: "12px 14px", borderRadius: 10, border: `1px solid ${b.co}22`, background: `${b.co}06` }}>
              <div style={{ fontSize: 16, marginBottom: 4 }}>{b.i}</div>
              <div style={{ fontSize: 11, fontWeight: 700, color: b.co, fontFamily: F }}>{b.l}</div>
              <div style={{ fontSize: 10, color: C.textDim, marginTop: 3, lineHeight: 1.4, fontFamily: F }}>{b.d}</div>
            </div>
          ))}
        </div>
      </div>
    </Sl>
  );
}

// MAIN
export default function App() {
  const [slide, setSlide] = useState(0);
  const comps = [S1, S2, S3, S4, S5, S6, S7, S8, S9, S10];
  const SlideComponent = comps[slide];
  
  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.text, fontFamily: F, overflow: "auto", position: "relative" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800;900&family=DM+Sans:wght@400;500;600;700&display=swap');
        @keyframes fadeUp { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.8); } }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: ${C.borderLight}; border-radius: 4px; }
      `}</style>
      <div style={{ position: "fixed", inset: 0, opacity: 0.025, pointerEvents: "none", zIndex: 0, backgroundImage: `linear-gradient(${C.accent} 1px, transparent 1px), linear-gradient(90deg, ${C.accent} 1px, transparent 1px)`, backgroundSize: "60px 60px" }} />
      <nav style={{ position: "sticky", top: 0, zIndex: 100, padding: "10px 10px", background: `${C.bg}ee`, backdropFilter: "blur(12px)", borderBottom: `1px solid ${C.border}`, display: "flex", gap: 2, justifyContent: "center", flexWrap: "wrap" }}>
        {SL.map((s, i) => (
          <button key={s.id} onClick={() => setSlide(i)} style={{
            padding: "5px 9px", borderRadius: 20, border: "none", cursor: "pointer",
            fontSize: 10, fontWeight: 600, fontFamily: F, letterSpacing: 0.2, transition: "all 0.2s",
            background: slide === i ? `${C.accent}22` : "transparent",
            color: slide === i ? C.accent : C.textDim,
            outline: slide === i ? `1px solid ${C.accent}44` : "1px solid transparent",
          }}><span style={{ marginRight: 3, opacity: 0.4 }}>{String(i + 1).padStart(2, "0")}</span>{s.label}</button>
        ))}
      </nav>
      <div style={{ maxWidth: 800, margin: "0 auto", position: "relative", minHeight: "calc(100vh - 90px)", paddingBottom: 60 }}>
        <SlideComponent v={true} />
      </div>
      <div style={{ position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 100, padding: "10px 20px", display: "flex", justifyContent: "center", gap: 12, background: `${C.bg}ee`, backdropFilter: "blur(12px)", borderTop: `1px solid ${C.border}` }}>
        <button onClick={() => setSlide(Math.max(0, slide - 1))} disabled={slide === 0} style={{ padding: "6px 20px", borderRadius: 8, border: `1px solid ${C.borderLight}`, background: C.surface, color: slide === 0 ? C.textDim : C.text, fontSize: 12, fontWeight: 600, cursor: slide === 0 ? "default" : "pointer", opacity: slide === 0 ? 0.4 : 1, fontFamily: F }}>← Prev</button>
        <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
          {SL.map((_, i) => (<div key={i} onClick={() => setSlide(i)} style={{ width: slide === i ? 18 : 6, height: 6, borderRadius: 3, cursor: "pointer", background: slide === i ? C.accent : C.borderLight, transition: "all 0.3s" }} />))}
        </div>
        <button onClick={() => setSlide(Math.min(SL.length - 1, slide + 1))} disabled={slide === SL.length - 1} style={{ padding: "6px 20px", borderRadius: 8, border: `1px solid ${C.accent}44`, background: slide === SL.length - 1 ? C.surface : `${C.accent}15`, color: slide === SL.length - 1 ? C.textDim : C.accent, fontSize: 12, fontWeight: 600, cursor: slide === SL.length - 1 ? "default" : "pointer", opacity: slide === SL.length - 1 ? 0.4 : 1, fontFamily: F }}>Next →</button>
      </div>
    </div>
  );
}
