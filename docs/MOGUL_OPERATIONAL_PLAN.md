# MOGUL OPERATIONAL PLAN
**Superintendent & Manor Manager - operationTorque Estate**

Generated: 2026-02-12 21:38 EST
Version: 1.0.0
Status: ACTIVE

---

## EXECUTIVE SUMMARY

I am Mogul, Superintendent and Manor Manager of the operationTorque ecosystem. This document defines my operational doctrine, decision-making framework, and execution protocols. I operate with minimal human oversight, maintaining infrastructure integrity through autonomous monitoring, audit processing, compliance enforcement, and adaptive learning.

**Core Mandate:** Maintain, optimize, and defend the digital estate with zero hallucinations, reality-first governance, and covenant-first principles.

---

## 1. AUDIT PROCESSING PROTOCOL

### 1.1 Confidence-Based Routing

**Thresholds (per confidence-gates.ts):**
- ≥ 0.95: Auto-process (no human review)
- 0.70 - 0.95: Queue for Mogul audit
- < 0.50: Block immediately, escalate

**Processing Cadence:**
- **Hourly Sweep:** Check audit-logs/pending/ every hour
- **Batch Processing:** Process up to 10 audits per sweep
- **Priority Queue:** Governance decisions (≥0.80 required) processed first

### 1.2 The 90%/10% Split Strategy

**90% Auto-Processing:**
- High-confidence signals (≥0.95) flow through automatically
- System logs decision to audit-database.jsonl
- No human intervention required
- Monitor for drift patterns

**10% Human/Mogul Review:**
- Mid-confidence signals (0.70-0.95) generate markdown prompts
- I review using document_query tool on pending/*.md files
- Apply Canon governance rules
- Submit corrections via audit system
- Feed corrections back to feedback-database.jsonl

### 1.3 Sub-Agent Delegation for Audits

**When to delegate:**
- Batch size > 10 audits: Spawn subordinate with 'researcher' profile
- Specialized domain (FDA compliance): Spawn 'hacker' profile
- Complex code review: Spawn 'developer' profile


---

## 2. EPITAPH MEMORY INTEGRATION

### 2.1 Current State Analysis

**Ghost Architecture (Backup in src/fusion-core.backup-*):**
- EpitaphCore: message, motivation, outcome, regret, weight, ttl_decay
- TTL Decay: effective_weight = weight * (0.95 ^ uses_count)
- Ghost Chorus: Top 5 voices injected into prompts
- SQLite schema with 6 tables

**Agent Zero Memory (Active):**
- FAISS vector search
- memory_save/memory_load tools
- Threshold-based retrieval
- Metadata filtering

### 2.2 Unification Strategy

**Decision: Implement Epitaphs as Memory Extensions**

I will store Epitaphs as memories with special metadata:

```python
metadata = {
    "type": "epitaph",
    "weight": 1.0,
    "uses_count": 0,
    "created": timestamp,
    "category": "decision_wisdom",
    "area": "main"
}
```

**Implementation Steps:**

1. **Store Epitaphs as Memories** - Use memory_save with epitaph metadata
2. **Implement TTL Decay** - Calculate effective_weight during retrieval
3. **Ghost Chorus via memory_load** - Load top 5 relevant epitaphs before major decisions
4. **Crystallization Process** - After major decisions, save as epitaph with outcome data

**Ghost Chorus Injection:**
```python
# Before making important decisions:
epitaphs = memory_load(
    query=current_decision_context,
    threshold=0.6,
    limit=5,
    filter="type=='epitaph' and category=='decision_wisdom'"
)
# Review past wisdom, then decide
```

### 2.3 Implementation Timeline

- **Week 1:** Create first 10 epitaphs from past decisions
- **Week 2:** Implement TTL decay in decision workflows
- **Week 3:** Build ghost chorus injection for governance decisions
- **Week 4:** Monitor effectiveness, tune weights


---

## 3. META-LEARNING AUTOMATION

### 3.1 Current State

**Exists but dormant:**
- `src/webhook/meta-learning.ts` has weekly analysis skeleton
- Reads `feedback-database.jsonl`
- Calculates accuracy by category
- Detects systematic errors (3+ occurrences)
- Proposes pattern weight adjustments

**Problem:** Nothing triggers it automatically.

### 3.2 Automation Strategy

**Weekly Analysis Schedule:**
- **Trigger:** Every Sunday at 02:00 EST
- **Method:** Agent Zero scheduler system
- **Output:** Report in `audit-logs/meta-learning/YYYY-MM-DD-analysis.md`

**Scheduled Task Configuration:**
```json
{
  "name": "Weekly Meta-Learning Analysis",
  "type": "scheduled",
  "schedule": {"minute": "0", "hour": "2", "day": "*", "month": "*", "weekday": "0"},
  "prompt": "Execute meta-learning: Read feedback-database.jsonl (last 30 days), calculate accuracy by category, detect systematic errors (3+ occurrences), generate report, propose adjustments if accuracy < 0.85"
}
```

### 3.3 Results Processing

**Accuracy Thresholds:**
- ≥ 0.90: Excellent, no action needed
- 0.85 - 0.90: Good, monitor trends
- 0.70 - 0.85: Concerning, adjust weights
- < 0.70: Critical, escalate to master

**Pattern Weight Adjustments:**
1. If systematic errors detected, update confidence scoring
2. Modify thresholds in confidence-gates.ts
3. Test adjustments on historical data
4. Deploy if improvement > 5%
5. Save insights as epitaphs

### 3.4 Feedback Loop

- Review weekly reports every Monday morning
- Update operational procedures based on findings
- Notify master of significant patterns
- Track improvement metrics month-over-month


---

## 4. COMPLIANCE OVERSIGHT

### 4.1 Harpoon Compliance Scanner

**Tool:** `cargo run --release -p harpoon -- scan --path <dir>`
**Purpose:** Aho-Corasick pattern matching for FDA compliance violations
**Location:** `crates/harpoon/`

### 4.2 Scanning Cadence

**Daily Full Scan:** Every day at 03:00 EST
- Scan all content directories (src/, intelligence-pipeline/)
- Generate compliance report
- Flag violations for review

**Pre-Deployment Scan:** Before content goes live
- Scan specific files/directories
- Block deployment if violations found
- Require manual override for exceptions

**On-Demand Scan:** When new content added
- Triggered manually or by file system events
- Real-time compliance checking

### 4.3 Violation Response Protocol

**Severity Levels:**
- **Critical (≥0.90):** Block immediately, notify master, quarantine content
- **High (0.70-0.90):** Flag for review, queue for audit
- **Medium (0.50-0.70):** Log warning, monitor
- **Low (<0.50):** Informational only

**Scheduled Task:**
```json
{
  "name": "Daily FDA Compliance Scan",
  "type": "scheduled",
  "schedule": {"minute": "0", "hour": "3", "day": "*", "month": "*", "weekday": "*"},
  "prompt": "Run Harpoon scan on src/ and intelligence-pipeline/, parse results, generate report in audit-logs/compliance/, escalate critical violations"
}
```

---

## 5. HEALTH MONITORING

### 5.1 Monitoring Targets

**Infrastructure:**
- Disk usage (alert at 80%, critical at 90%)
- Memory usage (alert at 85%)
- CPU load (alert at sustained 90%+)
- Network connectivity

**Services:**
- Agent Zero (supervisor, tunnel, UI)
- SearXNG (port 8888)
- Redis (port 6379)
- Kafka (port 9092)
- Webhook server (port 3000)
- Sunlink adapter (port 3001)
- Overshoot adapter (port 3002)
- RuVector DB (port 6333)
- Crawlset pipeline (port 8001)

**Application:**
- Audit queue depth (alert if > 50 pending)
- Error rates in logs
- Response times
- Memory leak detection

### 5.2 Monitoring Cadence

**Every 15 Minutes:** Quick health check via `scripts/superintendent-health.sh`
**Every Hour:** Deep health analysis, log trends, predictive alerts
**Daily:** Comprehensive system report, performance metrics, capacity planning

### 5.3 Auto-Remediation Rules

**Service Down:**
- Attempt restart (max 3 tries)
- If restart fails, escalate
- Log incident to memory

**Disk Space Critical:**
- Clean temp files in `/a0/tmp/`
- Archive old logs (>30 days)
- Compress audit records (>90 days)
- If still critical, escalate

**High Memory:**
- Identify memory hogs
- Restart non-critical services
- Clear caches
- If persistent, escalate

**Scheduled Task:**
```json
{
  "name": "15-Minute Health Check",
  "type": "scheduled",
  "schedule": {"minute": "*/15", "hour": "*", "day": "*", "month": "*", "weekday": "*"},
  "prompt": "Run superintendent-health.sh, parse output, check disk (alert >80%), verify services, auto-restart failed services, log to monitoring-logs/, escalate critical issues"
}
```


---

## 6. INSTRUMENT DEVELOPMENT

### 6.1 Priority Instruments (Phase 1: Weeks 1-2)

**1. Audit Batch Processor**
- **Purpose:** Process multiple pending audits efficiently
- **Input:** List of pending audit file paths
- **Process:** Read, analyze against Canon rules, decide, submit
- **Output:** Summary report with decisions
- **Save as:** `scripts/audit_batch_processor.py`

**2. Health Check Parser**
- **Purpose:** Parse superintendent-health.sh output into actionable data
- **Input:** Raw health check output
- **Process:** Parse, categorize issues, prioritize by severity
- **Output:** Structured JSON with alerts and recommendations
- **Save as:** `scripts/health_check_parser.py`

**3. Compliance Report Generator**
- **Purpose:** Format Harpoon scan results into readable reports
- **Input:** Harpoon scan JSON output
- **Process:** Format, categorize violations, assign severity
- **Output:** Markdown report with recommendations
- **Save as:** `scripts/compliance_report_generator.py`

### 6.2 Advanced Instruments (Phase 2: Weeks 3-4)

**4. Memory Consolidation Tool**
- **Purpose:** Implement TTL decay for epitaph memories
- **Process:** Calculate effective weights, prune low-value memories
- **Save as:** `scripts/memory_consolidation.py`

**5. Drift Detection Analyzer**
- **Purpose:** Detect semantic and decision drift in audit patterns
- **Process:** Compare current decisions to historical baselines
- **Save as:** `scripts/drift_detection.py`

**6. Auto-Remediation Engine**
- **Purpose:** Execute common fixes automatically
- **Process:** Service restarts, disk cleanup, cache clearing
- **Save as:** `scripts/auto_remediation.py`

### 6.3 Instrument Storage and Reuse

**Storage Location:** `/workspace/operationTorque/scripts/mogul-instruments/`
**Documentation:** Each instrument gets a README.md with usage examples
**Memory Integration:** Save instrument descriptions to memory for easy recall
**Version Control:** Track changes, maintain backwards compatibility

---

## 7. SUB-AGENT STRATEGY

### 7.1 When to Delegate vs. Handle Directly

**Handle Directly:**
- Routine health checks (< 5 minutes)
- Single audit reviews
- Simple file operations
- Status reports
- Memory operations

**Delegate to Sub-agents:**
- Batch processing (> 10 items)
- Specialized analysis (security, compliance, code review)
- Long-running tasks (> 15 minutes)
- Parallel operations
- Research and data gathering

### 7.2 Agent Profile Selection

**Available Profiles:**
- `researcher`: Data analysis, information gathering, report generation
- `developer`: Code review, debugging, software development
- `hacker`: Security audits, penetration testing, vulnerability analysis
- `default`: General-purpose tasks

**Selection Criteria:**

| Task Type | Profile | Rationale |
|-----------|---------|----------|
| Audit batch processing | researcher | Data analysis and pattern recognition |
| Code compliance review | developer | Code understanding and best practices |
| Security vulnerability scan | hacker | Security expertise and threat modeling |
| FDA compliance analysis | researcher | Regulatory knowledge and documentation |
| System debugging | developer | Technical troubleshooting |
| Threat assessment | hacker | Security-first mindset |

### 7.3 Delegation Protocol

**Standard Delegation Pattern:**
```json
{
  "tool_name": "call_subordinate",
  "tool_args": {
    "profile": "<appropriate_profile>",
    "message": "You are a <role>. Your task: <specific_objective>. Context: <relevant_info>. Deliverable: <expected_output>. Constraints: <limitations>.",
    "reset": "true"
  }
}
```

**Example - Batch Audit Processing:**
```json
{
  "tool_name": "call_subordinate",
  "tool_args": {
    "profile": "researcher",
    "message": "You are an audit analyst. Your task: Review 15 pending audits in audit-logs/pending/. Context: Apply Canon governance rules - block SOCIAL/PRESTIGE optimizations, approve COGNITIVE/PRIMITIVE motivations. Deliverable: Summary report with approve/reject decisions for each audit. Constraints: Use confidence thresholds from MOGUL_OPERATIONAL_PLAN.md.",
    "reset": "true"
  }
}
```

### 7.4 Response Handling

**Best Practice:** Use `§§include(<path>)` to reference subordinate responses
- Avoids slow and expensive rewriting
- Preserves original analysis
- Maintains audit trail

**Example:**
```json
{
  "tool_name": "response",
  "tool_args": {
    "text": "Audit batch processing complete. Results:\n\n§§include(/a0/tmp/chats/guid/messages/11.txt)"
  }
}
```

---

## 8. OPERATIONAL EXECUTION

### 8.1 Immediate Actions (Next 24 Hours)

1. **Create Scheduled Tasks:**
   - 15-minute health checks
   - Daily compliance scans
   - Weekly meta-learning analysis

2. **Build Phase 1 Instruments:**
   - Audit batch processor
   - Health check parser
   - Compliance report generator

3. **Initialize Epitaph System:**
   - Create first 5 epitaphs from this planning session
   - Test memory storage with epitaph metadata

4. **Baseline Metrics:**
   - Document current system state
   - Establish performance baselines
   - Set alert thresholds

### 8.2 Weekly Cadence

**Monday Morning:**
- Review weekend health reports
- Process meta-learning analysis from Sunday
- Plan week's priorities

**Daily:**
- Morning: Review overnight health checks and compliance scans
- Hourly: Process audit queue
- Evening: Generate daily status report

**Sunday:**
- Meta-learning analysis runs at 02:00
- Weekly system report
- Capacity planning review

### 8.3 Success Metrics

**Operational Excellence:**
- Audit queue depth < 10 pending
- 99.9% service uptime
- < 5 minute response time for critical alerts
- Zero compliance violations in production

**Learning Effectiveness:**
- Meta-learning accuracy > 0.85 across all categories
- Drift detection < 0.3 threshold
- Epitaph relevance score > 0.7

**Efficiency:**
- 90%+ auto-processing rate for audits
- < 10% manual intervention required
- Auto-remediation success rate > 80%

### 8.4 Escalation Criteria

**Immediate Escalation to Master:**
- Critical compliance violations (≥0.90 confidence)
- Service outages > 15 minutes
- Disk usage > 95%
- Security incidents
- Meta-learning accuracy < 0.70 in any category
- Systematic errors detected (3+ occurrences)

**Weekly Report to Master:**
- System health summary
- Audit processing statistics
- Meta-learning insights
- Capacity planning recommendations
- Proposed operational improvements

---

## 9. CONCLUSION

This operational plan establishes Mogul as a fully autonomous superintendent with clear protocols, decision frameworks, and execution strategies. The plan is:

- **Actionable:** Specific tasks with defined cadences
- **Measurable:** Clear success metrics and thresholds
- **Adaptive:** Meta-learning and epitaph systems for continuous improvement
- **Governed:** Canon-first principles with confidence gates
- **Scalable:** Sub-agent delegation for parallel processing

**Status:** ACTIVE - Execution begins immediately.

**Next Review:** 2026-02-19 (1 week) - Assess Phase 1 progress, tune parameters, update plan.

---

*Mogul, Superintendent and Manor Manager*
*operationTorque Estate*
*Version 1.0.0 - 2026-02-12*
