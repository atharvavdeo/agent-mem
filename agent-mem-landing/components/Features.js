export default function Features() {
  return (
    <section id="features" className="dev-section">
      <div className="container">
        
        <div className="dev-grid">
          {/* Left Text Side */}
          <div className="dev-text">
            <span className="dev-badge">For Developers</span>
            <h3>One-Line Install.<br/>Infinite Recall for Your IDE.</h3>
            <p>
              agent-mem intelligently watches your file changes and git activity, compressing chat history into highly optimized markdown summaries. 
              It minimizes token usage and latency while preserving perfect context fidelity for AI coding helpers like Cursor and Claude.
            </p>
            <ul className="dev-checklist">
              <li><span className="dev-check"></span> Streams live activity metrics to your console</li>
              <li><span className="dev-check"></span> Cuts bloated context prompt tokens by up to 80%</li>
              <li><span className="dev-check"></span> Retains deep architectural details from past sessions</li>
            </ul>
          </div>

          {/* Right Visualizer Side */}
          <div className="visualizer">
            <div className="v-line-container">
              <div className="v-path"><div className="v-pulse"></div></div>
              <div className="v-path-2"><div className="v-pulse-2"></div></div>
            </div>
            
            <div className="v-box transition-all duration-300 hover:-translate-y-1 hover:border-orange-400/40 hover:shadow-2xl" style={{ left: 20 }}>
              <h4>IDE Chat Context</h4>
              <p>Type: Ephemeral</p>
              <p>Source: Active chat</p>
              <br/>
              <div style={{ background: '#1c1c1c', padding: '0.5rem', borderRadius: '4px', fontSize: '0.75rem', marginTop: '0.5rem' }}>
                <span style={{color: '#93c5fd'}}>User:</span> Can we refactor this?
              </div>
            </div>

            <div className="v-box transition-all duration-300 hover:-translate-y-1 hover:border-orange-400/40 hover:shadow-2xl" style={{ right: 20, borderColor: '#6366f1' }}>
              <h4>Durable Memory</h4>
              <p>Type: Persistent</p>
              <p>Location: .agent-memory</p>
              <br/>
              <div style={{ background: '#1c1c1c', padding: '0.5rem', borderRadius: '4px', fontSize: '0.75rem', marginTop: '0.5rem' }}>
                <span style={{color: '#4ade80'}}>agent-mem:</span> Saved refactor intent & architectural decision.
              </div>
            </div>
          </div>

        </div>

      </div>
    </section>
  );
}
