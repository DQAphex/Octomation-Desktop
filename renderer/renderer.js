const statusEl = document.getElementById("status");
const pidEl = document.getElementById("pid");
const resultEl = document.getElementById("result");

const btnLoadPlugins = document.getElementById("btnLoadPlugins");
const pluginsList = document.getElementById("pluginsList");
const pluginsResult = document.getElementById("pluginsResult");

let API_BASE = null;

async function getApiBase() {
    API_BASE = `http://127.0.0.1:8000`;
    return API_BASE;
}

function setStatus(running) {
  if (running) {
    statusEl.textContent = "● Servidor en línea";
    statusEl.classList.remove("offline");
    statusEl.classList.add("online");
    document.getElementById("btnStop").disabled = false;
    document.getElementById("btnRestart").disabled = false;
  } else {
    statusEl.textContent = "● Servidor apagado";
    statusEl.classList.remove("online");
    statusEl.classList.add("offline");
    document.getElementById("btnStop").disabled = true;
    document.getElementById("btnRestart").disabled = false;
    pidEl.textContent = "PID: -";
  }
}

function setPid(pid) {
  if (pid) {
    pidEl.textContent = `PID: ${pid}`;
  } else {
    pidEl.textContent = "PID: -";
  }
}

if (window.api) {
  window.api.onPortUpdate((port) => {
    if (port && port !== 'null') {
      window.API_PORT = port;
      API_BASE = `http://127.0.0.1:${port}`;
      resultEl.textContent = `Servidor FastAPI listo en http://127.0.0.1:${port}`;
    }
    setStatus(true);
  });

  window.api.onStatusUpdate((status) => {
    setStatus(status.running);
  });

  window.api.onPidUpdate((pid) => {
    setPid(pid);
  });

  window.api.getFastApiPort().then((port) => {
    if (port) {
      window.API_PORT = port;
      API_BASE = `http://127.0.0.1:${port}`;
      setStatus(true);
    }
  });
}

document.getElementById("btnHealth").addEventListener("click", async () => {
  try {
    const base = await getApiBase();
    const res = await fetch(`${base}/health`);

    if (!res.ok) {
      throw new Error(`Error HTTP: ${res.status}`);
    }

    const data = await res.json();
    resultEl.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    resultEl.textContent = `Error: ${err.message}`;
  }
});

document.getElementById("btnRoot").addEventListener("click", async () => {
  try {
    const base = await getApiBase();
    const res = await fetch(`${base}/`);

    if (!res.ok) {
      throw new Error(`Error HTTP: ${res.status}`);
    }

    const data = await res.json();
    resultEl.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    resultEl.textContent = `Error: ${err.message}`;
  }
});

document.getElementById("btnHola").addEventListener("click", async () => {
  try {
    const base = await getApiBase();
    const res = await fetch(`${base}/hola`);

    if (!res.ok) {
      throw new Error(`Error HTTP: ${res.status}`);
    }

    const data = await res.json();
    resultEl.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    resultEl.textContent = `Error: ${err.message}`;
  }
});

document.getElementById("btnStop").addEventListener("click", async () => {
  resultEl.textContent = "Apagando servidor FastAPI...";
  const res = await window.api.stopFastAPI();
  resultEl.textContent = res.message;
  setStatus(false);
  setPid(null);
});

document.getElementById("btnRestart").addEventListener("click", async () => {
  resultEl.textContent = "Reiniciando servidor FastAPI...\nEspera un momento...";
  document.getElementById("btnStop").disabled = true;
  document.getElementById("btnRestart").disabled = true;
  const res = await window.api.restartFastAPI();
  resultEl.textContent = res.message + "\n\nEl servidor se está levantando de nuevo...";
});

btnLoadPlugins.addEventListener("click", async () => {
  pluginsList.innerHTML = "";
  pluginsResult.textContent = "Cargando plugins desde http://localhost:4005/plugins...";
  btnLoadPlugins.disabled = true;

  try {
    const res = await window.api.getAvailablePlugins();
    if (!res.success) {
      pluginsResult.textContent = "Error: " + res.error;
      btnLoadPlugins.disabled = false;
      return;
    }

    const plugins = res.data;
    if (!Array.isArray(plugins) || plugins.length === 0) {
      pluginsResult.textContent = "No hay plugins disponibles en el catálogo.";
      btnLoadPlugins.disabled = false;
      return;
    }

    plugins.forEach((plugin) => {
      const card = document.createElement("div");
      card.className = "plugin-card";
      card.innerHTML = `
        <h3>${plugin.name}</h3>
        <div class="plugin-meta">
          <span><strong>Categoría:</strong> ${plugin.pluginCategory}</span>
          <span><strong>Autor:</strong> ${plugin.author} (${plugin.email})</span>
          <span><strong>Versión:</strong> ${plugin.latestVersion} (${plugin.releaseTag})</span>
          <span><strong>Repositorio:</strong> ${plugin.repositoryUrl}</span>
        </div>
        <div class="plugin-actions">
          <button class="btn-download" data-id="${plugin.pluginId}">⬇️ Descargar y extraer</button>
        </div>
      `;
      pluginsList.appendChild(card);
    });

    pluginsResult.textContent = `Se encontraron ${plugins.length} plugin(s). Pulsa "Descargar y extraer" para guardarlos en ./plugins/`;

    document.querySelectorAll(".btn-download").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const pluginId = btn.getAttribute("data-id");
        btn.disabled = true;
        btn.classList.add("downloading");
        btn.textContent = "⏳ Descargando...";
        pluginsResult.textContent = `Obteniendo información de descarga para ${pluginId}...`;

        const dl = await window.api.downloadPlugin(pluginId);
        if (dl.success) {
          pluginsResult.textContent = dl.message + "\n\nRevisa la carpeta: electron-fastapi-app/plugins/";
          btn.textContent = "✅ Extraído";
        } else {
          pluginsResult.textContent = "Error: " + dl.error;
          btn.disabled = false;
          btn.classList.remove("downloading");
          btn.textContent = "⬇️ Descargar y extraer";
        }
      });
    });
  } catch (err) {
    pluginsResult.textContent = "Error inesperado: " + err.message;
  }

  btnLoadPlugins.disabled = false;
});
