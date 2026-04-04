import "./globals.css";
import { Toaster } from "react-hot-toast";
import Navbar from "@/components/Navbar";

export const metadata = {
  title: "CADguard — AI-Powered CAD Validation",
  description:
    "Analyze CAD files for manufacturability risks using explainable AI. Get instant DFM insights, SHAP-based explanations, and actionable recommendations.",
  keywords: [
    "CAD validation",
    "DFM",
    "manufacturability",
    "SHAP",
    "explainable AI",
  ],
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
      </head>
      <body className="min-h-screen bg-surface-900 bg-grid-pattern">
        {/* Background ambient glow */}
        <div className="fixed inset-0 pointer-events-none overflow-hidden">
          <div className="absolute -top-1/2 -left-1/4 w-[600px] h-[600px] rounded-full bg-brand-600/5 blur-[120px]" />
          <div className="absolute -bottom-1/2 -right-1/4 w-[500px] h-[500px] rounded-full bg-brand-400/5 blur-[100px]" />
        </div>

        <div className="relative z-10">
          <Navbar />
          <main className="pt-20">{children}</main>
        </div>

        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: "rgba(15, 23, 42, 0.9)",
              color: "#f8fafc",
              border: "1px solid rgba(99, 102, 241, 0.2)",
              backdropFilter: "blur(12px)",
              borderRadius: "12px",
              fontSize: "14px",
            },
            success: {
              iconTheme: {
                primary: "#10b981",
                secondary: "#020617",
              },
            },
            error: {
              iconTheme: {
                primary: "#ef4444",
                secondary: "#020617",
              },
            },
          }}
        />
      </body>
    </html>
  );
}
