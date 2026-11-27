import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";
import "./platform.css";
import "./agent.css";
import "@fontsource-variable/schibsted-grotesk";
import "@fontsource/martian-mono/400.css";
import "@fontsource/martian-mono/600.css";
import "./grid.css";

// Public offline explanation only. Sensitive responses are never cached by our worker.
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => { void navigator.serviceWorker.register("/sw.js", { updateViaCache: "none" }).catch(() => undefined); });
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
