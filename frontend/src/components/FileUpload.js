"use client";

import { useCallback, useState } from "react";

/**
 * FileUpload — Drag-and-drop file upload with visual feedback.
 * Accepts .stl files and any other file for demo simulation.
 */
export default function FileUpload({ onFileSelect, disabled }) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const files = e.dataTransfer?.files;
      if (files && files.length > 0) {
        const file = files[0];
        setSelectedFile(file);
        onFileSelect?.(file);
      }
    },
    [onFileSelect]
  );

  const handleFileInput = useCallback(
    (e) => {
      const file = e.target.files?.[0];
      if (file) {
        setSelectedFile(file);
        onFileSelect?.(file);
      }
    },
    [onFileSelect]
  );

  const clearFile = useCallback(() => {
    setSelectedFile(null);
    onFileSelect?.(null);
  }, [onFileSelect]);

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="w-full">
      {!selectedFile ? (
        <div
          className={`dropzone rounded-2xl p-10 text-center cursor-pointer transition-all duration-300 ${
            isDragging ? "active border-brand-400" : ""
          } ${disabled ? "opacity-50 pointer-events-none" : ""}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => document.getElementById("file-input")?.click()}
          id="upload-dropzone"
        >
          <input
            id="file-input"
            type="file"
            className="hidden"
            accept=".stl,.STL,.step,.stp,.obj,.txt"
            onChange={handleFileInput}
            disabled={disabled}
          />

          {/* Upload Icon */}
          <div className="mx-auto w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mb-5">
            <svg
              className={`w-8 h-8 transition-all duration-300 ${
                isDragging ? "text-brand-400 scale-110" : "text-brand-500/60"
              }`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
              />
            </svg>
          </div>

          <h3 className="text-lg font-semibold text-slate-200 mb-2">
            {isDragging ? "Drop your file here" : "Upload CAD File"}
          </h3>
          <p className="text-sm text-slate-400 mb-4">
            Drag and drop your file or{" "}
            <span className="text-brand-400 font-medium">browse</span>
          </p>
          <div className="flex items-center justify-center gap-2 text-xs text-slate-500">
            <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
              .STL
            </span>
            <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
              .STEP
            </span>
            <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
              .OBJ
            </span>
            <span className="text-slate-600">or any file for demo</span>
          </div>
        </div>
      ) : (
        <div className="glass-card p-5 animate-fade-in">
          <div className="flex items-center gap-4">
            {/* File icon */}
            <div className="w-12 h-12 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center flex-shrink-0">
              <svg
                className="w-6 h-6 text-brand-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                />
              </svg>
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-200 truncate">
                {selectedFile.name}
              </p>
              <p className="text-xs text-slate-500">
                {formatSize(selectedFile.size)}
              </p>
            </div>

            {/* Remove button */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                clearFile();
              }}
              className="p-2 rounded-lg hover:bg-red-500/10 text-slate-500 hover:text-red-400 transition-all duration-200"
              title="Remove file"
              id="remove-file-btn"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* Success indicator */}
          <div className="mt-3 flex items-center gap-2 text-xs text-emerald-400">
            <svg
              className="w-3.5 h-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4.5 12.75l6 6 9-13.5"
              />
            </svg>
            File ready for analysis
          </div>
        </div>
      )}
    </div>
  );
}
