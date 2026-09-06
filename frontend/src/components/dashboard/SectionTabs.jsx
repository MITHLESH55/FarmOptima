import React from "react";
import { Activity, BarChart3, SlidersHorizontal } from "lucide-react";
import { t } from "../../i18n";

export default function SectionTabs({ activeTab, onChange, children, locale }) {
  const tabs = [
    { id: "live", label: t("tabs.liveFieldData", locale), icon: <Activity className="w-4 h-4" /> },
    { id: "ahp", label: t("tabs.ahpRanking", locale), icon: <BarChart3 className="w-4 h-4" /> },
    { id: "plan", label: t("tabs.planRationale", locale), icon: <SlidersHorizontal className="w-4 h-4" /> },
  ];

  return (
    <div className="space-y-6">
      {/* Tab Navigation Header */}
      <div className="border-b border-ink-secondary/15 bg-surface/60 rounded-xl p-1.5 shadow-sm">
        <nav className="flex space-x-2" aria-label="Tabs">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onChange(tab.id)}
                className={`flex items-center gap-2 px-5 py-3 rounded-lg text-sm font-semibold transition-all ${
                  isActive
                    ? "bg-brand-primary text-surface shadow-md"
                    : "text-ink-secondary hover:text-ink-primary hover:bg-base"
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content Panel */}
      <div className="tab-content transition-opacity duration-300">
        {children}
      </div>
    </div>
  );
}
