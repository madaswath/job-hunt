import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ClerkProvider } from "@clerk/clerk-react";
import App from "./App";
import { initTheme } from "./lib/theme";
import "./index.css";

initTheme();
const clerkKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
const root = createRoot(document.getElementById("root")!);
const tree = (
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);

root.render(
  clerkKey ? (
    <ClerkProvider publishableKey={clerkKey}>{tree}</ClerkProvider>
  ) : (
    tree
  ),
);
