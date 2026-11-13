import { useEffect, useRef, useState } from "react";

export default function Dashboard() {
  const [apiBase, setApiBase] = useState<string | null>(null);
  const [status, setStatus] = useState<"online" | "offline">("online");
  const [pid, setPid] = useState<string>("-");
  const [result, setResult] = useState("Pulsa un botón para probar...");
  const [plugins, setPlugins] = useState<any[]>([]);
  const [pluginsResult, setPluginsResult] = useState("Aún no se han cargado plugins...");
  const [loadingPlugins, setLoadingPlugins] = useState(false);

  const resultRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    if (!window.api) return;

    window.api.onPortUpdate((port) => {
      if (port) {
        window.API_PORT = port;
        setApiBase(`http://127.0.0.1:${port}`);
        setResult(`Servidor FastAPI listo en http://127.0.0.1:${port}`);
      }
      setStatus("online");
    });

    window.api.onStatusUpdate((s) => {
      setStatus(s.running ? "online" : "offline");
      if (!s.running) setPid("-");
    });

    window.api.onPidUpdate((p) => {
      setPid(p ? String(p) : "-");
    });

    window.api.getFastApiPort().then((port) => {
      if (port) {
        window.API_PORT = port;
        setApiBase(`http://127.0.0.1:${port}`);
        setStatus("online");
      }
    });
  }, []);

  const getBase = async () => {
    if (apiBase) return apiBase;
    const port = await window.api.getFastApiPort();
    const base = `http://127.0.0.1:${port || 8000}`;
    setApiBase(base);
    return base;
  };

  const callHealth = async () => {
    try {
      const base = await getBase();
      const res = await fetch(`${base}/health`);
      if (!res.ok) throw new Error(`Error HTTP: ${res.status}`);
      const data = await res.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (err: any) {
      setResult(`Error: ${err.message}`);
    }
  };

  const callRoot = async () => {
    try {
      const base = await getBase();
      const res = await fetch(`${base}/`);
      if (!res.ok) throw new Error(`Error HTTP: ${res.status}`);
      const data = await res.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (err: any) {
      setResult(`Error: ${err.message}`);
    }
  };

  const callHola = async () => {
    try {
      const base = await getBase();
      const res = await fetch(`${base}/hola`);
      if (!res.ok) throw new Error(`Error HTTP: ${res.status}`);
      const data = await res.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (err: any) {
      setResult(`Error: ${err.message}`);
    }
  };

  const stop = async () => {
    setResult("Apagando servidor FastAPI...");
    const res = await window.api.stopFastAPI();
    setResult(res.message);
    setStatus("offline");
    setPid("-");
  };

  const restart = async () => {
    setResult("Reiniciando servidor FastAPI...\nEspera un momento...");
    const res = await window.api.restartFastAPI();
    setResult(res.message + "\n\nEl servidor se está levantando de nuevo...");
  };

  const loadPlugins = async () => {
    setLoadingPlugins(true);
    setPlugins([]);
    setPluginsResult("Cargando plugins desde http://localhost:4005/plugins...");
    try {
      const res = await window.api.getAvailablePlugins();
      if (!res.success) {
        setPluginsResult("Error: " + res.error);
        return;
      }
      const list = res.data || [];
      if (list.length === 0) {
        setPluginsResult("No hay plugins disponibles en el catálogo.");
        return;
      }
      setPlugins(list);
      setPluginsResult(`Se encontraron ${list.length} plugin(s). Pulsa "Descargar y extraer" para guardarlos en ./plugins/`);
    } catch (err: any) {
      setPluginsResult("Error inesperado: " + err.message);
    } finally {
      setLoadingPlugins(false);
    }
  };

  const downloadPlugin = async (pluginId: string, btn: HTMLButtonElement) => {
    btn.disabled = true;
    btn.classList.add("downloading");
    btn.textContent = "⏳ Descargando...";
    setPluginsResult(`Obteniendo información de descarga para ${pluginId}...`);
    try {
      const dl = await window.api.downloadPlugin(pluginId);
      if (dl.success) {
        setPluginsResult(dl.message + "\n\nRevisa la carpeta: electron-fastapi-app/plugins/");
        btn.textContent = "✅ Extraído";
      } else {
        setPluginsResult("Error: " + dl.error);
        btn.disabled = false;
        btn.classList.remove("downloading");
        btn.textContent = "⬇️ Descargar y extraer";
      }
    } catch (err: any) {
      setPluginsResult("Error: " + err.message);
      btn.disabled = false;
      btn.classList.remove("downloading");
      btn.textContent = "⬇️ Descargar y extraer";
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Inicio</h1>
          <p>App conectada a servidor FastAPI local</p>
        </div>
      </div>

      <div className="server-controls">
        <span className={`status ${status}`}>● Servidor {status === "online" ? "en línea" : "apagado"}</span>
        <span className="pid">PID: {pid}</span>
        <div className="buttons">
          <button id="btnStop" className="btn-danger" onClick={stop} disabled={status === "offline"}>
            <span className="material-symbols-outlined">
              power_off
            </span>
            Apagar servidor
          </button>
          <button id="btnRestart" className="btn-warning" onClick={restart}>
            <span className="material-symbols-outlined">
              refresh
            </span>
            Reiniciar servidor
          </button>
        </div>
      </div>

      <div className="buttons">
        <button onClick={callHealth}><span className="material-symbols-outlined">health_metrics</span>Comprobar /health</button>
      </div>

      <pre ref={resultRef}>{result}</pre>
    </div>
  );
}
