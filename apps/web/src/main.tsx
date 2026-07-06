/**
 * IaaS-RonSys — Frontend Web
 *
 * Entry point de la aplicación React.
 * Monta el árbol de componentes en el DOM y aplica los estilos globales.
 *
 * @module main
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
