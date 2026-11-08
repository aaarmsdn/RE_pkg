import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./style.css";
import "./bulkReview.css";
const root = document.getElementById("root");
if (root) createRoot(root).render(<App />);
