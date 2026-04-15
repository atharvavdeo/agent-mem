import Link from 'next/link';

export default function Navbar() {
  return (
    <nav className="navbar">
      <div className="container inner">
        <Link href="/" className="logo">
          <img src="/logo.png" alt="agent-mem logo" />
          agent-mem
        </Link>
        <div className="links">
          <Link href="#features">Features</Link>
          <Link href="#features">Developers</Link>
          <Link href="https://github.com/atharvavdeo/agent-mem" target="_blank">GitHub</Link>
        </div>
      </div>
    </nav>
  );
}
