import { Route, Routes } from "react-router-dom";
import Workspace from "./pages/Workspace";
import { SimulationProvider } from "./hooks/SimulationContext";

export default function App() {
  return (
    <SimulationProvider>
    <Routes><Route path="*" element={<Workspace />} /></Routes>
    </SimulationProvider>
  );
}
