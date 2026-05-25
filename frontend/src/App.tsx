import { NavLink, Route, Routes, Navigate } from "react-router-dom";
import DrawsPage from "./pages/Draws";
import PredictPage from "./pages/Predict";
import HistoryPage from "./pages/History";
import AggregatePage from "./pages/Aggregate";
import FrequencyPage from "./pages/Frequency";
import ModelPage from "./pages/Model";

export default function App() {
  return (
    <>
      <nav>
        <NavLink to="/draws" className={({ isActive }) => (isActive ? "active" : "")}>
          训练集
        </NavLink>
        <NavLink to="/predict" className={({ isActive }) => (isActive ? "active" : "")}>
          生成预测
        </NavLink>
        <NavLink to="/model" className={({ isActive }) => (isActive ? "active" : "")}>
          预测模型
        </NavLink>
        <NavLink to="/aggregate" className={({ isActive }) => (isActive ? "active" : "")}>
          聚合选号
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => (isActive ? "active" : "")}>
          历史与评估
        </NavLink>
        <NavLink to="/frequency" className={({ isActive }) => (isActive ? "active" : "")}>
          频率统计
        </NavLink>
      </nav>
      <div className="container">
        <Routes>
          <Route path="/" element={<Navigate to="/draws" replace />} />
          <Route path="/draws" element={<DrawsPage />} />
          <Route path="/predict" element={<PredictPage />} />
          <Route path="/model" element={<ModelPage />} />
          <Route path="/aggregate" element={<AggregatePage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/frequency" element={<FrequencyPage />} />
        </Routes>
      </div>
    </>
  );
}
