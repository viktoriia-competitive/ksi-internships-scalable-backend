"use client";

import Editor, { type OnChange } from "@monaco-editor/react";
import type { RuntimeName } from "@/lib/contracts";

const RUNTIME_MODE: Record<RuntimeName, string> = {
  "C++": "cpp",
  Python: "python",
  Java: "java",
  Rust: "rust",
  Go: "go",
  SQL: "sql",
  Bash: "shell",
};

const EDITOR_OPTIONS = {
  automaticLayout: true,
  domReadOnly: false,
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
  fontSize: 14,
  minimap: { enabled: false },
  padding: { top: 12, bottom: 12 },
  readOnly: false,
  renderLineHighlight: "line" as const,
  scrollBeyondLastLine: false,
  tabSize: 4,
  wordWrap: "on" as const,
};

type CodeEditorProps = {
  runtime: RuntimeName;
  value: string;
  onChange: (value: string) => void;
};

export function CodeEditor({ runtime, value, onChange }: CodeEditorProps) {
  const handleChange: OnChange = (nextValue) => onChange(nextValue ?? "");

  return (
    <div className="monaco-wrap" data-runtime={runtime}>
      <Editor
        height="100%"
        language={RUNTIME_MODE[runtime]}
        value={value}
        theme="vs-dark"
        onChange={handleChange}
        options={EDITOR_OPTIONS}
        loading={<div className="monaco-loading">Preparing editor…</div>}
      />
    </div>
  );
}
