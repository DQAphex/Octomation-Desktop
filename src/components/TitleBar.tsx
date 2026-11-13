
import './TitleBar.css';

export default function TitleBar() {
  return (
    <header className="titlebar">
      <div className="titlebar-brand">
        Octomation
      </div>

      <div className="titlebar-actions">
        <button
          onClick={() => window.api.minimize()}
          aria-label="Minimizar"
          title="Minimizar"
        >
        <span className="material-symbols-outlined">minimize</span>
        </button>

        <button
          onClick={() => window.api.maximize()}
          aria-label="Maximizar o restaurar"
          title="Maximizar o restaurar"
        >
        <span className="material-symbols-outlined">open_in_full</span>
        </button>

        <button
          onClick={() => window.api.close()}
          aria-label="Cerrar"
          title="Cerrar"
        >
        <span className="material-symbols-outlined">close</span>
        </button>
      </div>
    </header>
  );
}
