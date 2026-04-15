export default function TerminalDemo() {
  return (
    <div className="container" style={{ marginBottom: '6rem' }}>
      <div className="terminal-wrap">
        <div className="terminal-header">
          <span className="dot dot-r"></span>
          <span className="dot dot-y"></span>
          <span className="dot dot-g"></span>
          <span className="terminal-title">bash — agent-mem</span>
        </div>
        <div className="terminal-body">
          <div className="t-line">
            <span className="t-prompt">$</span>
            <span className="t-cmd">agent-mem init</span>
          </div>
          <div className="t-line">
            <span className="t-prompt"> </span>
            <span className="t-success">✔ Initialized .agent-memory/ in project root</span>
          </div>
          <div className="t-line">
            <span className="t-prompt"> </span>
            <span className="t-success">✔ AGENTS.md rules written</span>
          </div>
          <div className="t-line" style={{ marginTop: '0.5rem' }}>
            <span className="t-prompt">$</span>
            <span className="t-cmd">agent-mem watch</span>
          </div>
          <div className="t-line">
            <span className="t-prompt"> </span>
            <span className="t-info">👁  Watching for meaningful changes...</span>
          </div>
          <div className="t-line">
            <span className="t-prompt"> </span>
            <span className="t-info">✔  Milestone detected in src/agent_mem/cli.py</span>
          </div>
          <div className="t-line">
            <span className="t-prompt"> </span>
            <span className="t-success">✨ Memory updated &amp; handoff copied to clipboard!</span>
          </div>
          <div className="t-line">
            <span className="t-prompt"> </span>
            <span className="t-blue">📋 Paste the handoff prompt into your IDE agent.</span>
          </div>
          <div className="t-line" style={{ marginTop: '0.5rem' }}>
            <span className="t-prompt">$</span>
            <span className="cursor"></span>
          </div>
        </div>
      </div>
    </div>
  );
}
