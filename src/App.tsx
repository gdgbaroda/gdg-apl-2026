import { useEffect, useState } from 'react';
import challenges from './challenges.json';
import gdgLogo from './assets/gdg-baroda.png';
import batsman from './assets/apl-batsman.jpg';

type Challenge = {
  innings: number;
  title: string;
  prompt: string;
};

export default function App() {
  const [idx, setIdx] = useState(0);
  const c = (challenges as Challenge[])[idx];

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === ' ') {
        setIdx((i) => Math.min(i + 1, challenges.length - 1));
      } else if (e.key === 'ArrowLeft') {
        setIdx((i) => Math.max(i - 1, 0));
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="strip">
      <div className="brand">
        <div className="brand-top">Google Cloud</div>
        <div className="brand-event">
          Build with AI <span className="dot">·</span> Agentic Premier League
        </div>
        <div className="brand-host">
          <img src={gdgLogo} alt="GDG Baroda" />
        </div>
      </div>

      <div className="body">
        <div className="title">
          <span className="innings-pill">INNINGS {c.innings}</span>
          {c.title}
        </div>
        <div className="prompt">{c.prompt}</div>
      </div>

      <div className="hero">
        <img src={batsman} alt="" />
      </div>
    </div>
  );
}
