import './globals.css';
import Navbar from '../components/Navbar';
import { Inter, Roboto_Mono } from 'next/font/google';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
});

const robotoMono = Roboto_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
});

export const metadata = {
  title: 'agent-mem — Persistent Memory for AI Coding Agents',
  description: 'Stop repeating yourself. Give your IDE agent durable, context-aware memory that persists across chats.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${robotoMono.variable}`}>
        <Navbar />
        {children}
        <footer className="footer">
          <div className="container">
            <p>© 2026 agent-mem · MIT License · Made for builders.</p>
            <div className="footer-links">
              <a href="https://github.com/atharvavdeo/agent-mem" target="_blank">GitHub</a>
              <a href="https://pypi.org/project/easy-agent-mem/" target="_blank">PyPI</a>
              <a href="https://github.com/atharvavdeo/agent-mem/blob/main/LICENSE" target="_blank">License</a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
