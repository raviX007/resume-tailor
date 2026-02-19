"use client";

import { useCallback, useRef, useState } from "react";
import { tailorResumeStream, type SSEProgressEvent, type SSEErrorEvent } from "@/lib/api";
import type { TailorResponse } from "@/lib/types";
import { JdInputPanel } from "@/components/jd-input-panel";
import { ResultsPanel } from "@/components/results-panel";
import { ErrorBoundary } from "@/components/error-boundary";

const PIPELINE_STEPS = [
  "Analyzing resume...",
  "Extracting keywords...",
  "Matching skills...",
  "Computing reorder plan...",
  "Injecting into LaTeX...",
  "Compiling PDF...",
];

export default function Home() {
  const [jdText, setJdText] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [result, setResult] = useState<TailorResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const handleTailor = useCallback(async () => {
    if (jdText.trim().length < 50 || !resumeFile) return;

    // Cancel any in-flight request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    setResult(null);
    setStep(PIPELINE_STEPS[0]);

    await tailorResumeStream(
      {
        jd_text: jdText,
        job_title: jobTitle || undefined,
        company_name: companyName || undefined,
        resume_file: resumeFile,
      },
      {
        onStep: (event: SSEProgressEvent) => {
          setStep(PIPELINE_STEPS[event.step] ?? `Step ${event.step}...`);
        },
        onComplete: (response: TailorResponse) => {
          setResult(response);
          setStep(null);
          setLoading(false);
          abortRef.current = null;
        },
        onError: (err: SSEErrorEvent | Error) => {
          if (controller.signal.aborted) return;
          const message = err instanceof Error
            ? err.message
            : err.detail;
          setError(message);
          setStep(null);
          setLoading(false);
          abortRef.current = null;
        },
      },
      controller.signal,
    );

    // Stream ended without onComplete/onError (e.g., unexpected close)
    setLoading((prev) => {
      if (prev) {
        setStep(null);
        abortRef.current = null;
      }
      return false;
    });
  }, [jdText, jobTitle, companyName, resumeFile]);

  const handleCancel = useCallback(() => {
    abortRef.current?.abort();
    setLoading(false);
    setStep(null);
  }, []);

  return (
    <main className="h-screen flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-gray-200 bg-white shrink-0 shadow-sm">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <span className="text-lg font-bold text-gray-900">Resume Tailor</span>
        </div>
        <span className="text-xs text-gray-400">LLM + LaTeX powered</span>
      </header>

      {/* Panels — stacks vertically on mobile */}
      <div className="flex flex-col md:flex-row flex-1 min-h-0">
        {/* Left Panel — Input */}
        <div className="w-full md:w-1/2 border-b md:border-b-0 md:border-r border-gray-200 bg-gray-50/80 p-4 md:p-6 flex flex-col overflow-y-auto shadow-[inset_-6px_0_12px_-6px_rgba(0,0,0,0.04)]">
          <JdInputPanel
            jdText={jdText}
            jobTitle={jobTitle}
            companyName={companyName}
            resumeFile={resumeFile}
            onJdChange={setJdText}
            onJobTitleChange={setJobTitle}
            onCompanyChange={setCompanyName}
            onFileChange={setResumeFile}
            onSubmit={handleTailor}
            loading={loading}
            step={step}
          />
          {loading && (
            <button
              onClick={handleCancel}
              aria-label="Cancel resume tailoring"
              className="mt-2 w-full py-2 text-sm text-gray-500 hover:text-red-500 transition-colors"
            >
              Cancel
            </button>
          )}
        </div>

        {/* Right Panel — Results */}
        <div className="w-full md:w-1/2 bg-white p-4 md:p-6 overflow-y-auto">
          <ErrorBoundary>
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-600 text-sm" role="alert">
                <p className="font-semibold text-red-700">Error</p>
                <p className="mt-1">{error}</p>
              </div>
            )}

            {result && <ResultsPanel result={result} companyName={companyName} />}

            {!result && !error && !loading && (
              <div className="h-full flex items-center justify-center">
                <div className="text-center">
                  <svg className="w-16 h-16 mx-auto mb-4 text-gray-300 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p className="text-lg font-medium text-gray-500">Upload a .tex resume and paste a JD</p>
                  <p className="text-sm mt-1 text-gray-400">Your tailored resume will appear here</p>
                </div>
              </div>
            )}

            {loading && !result && (
              <div className="h-full flex items-center justify-center">
                <div className="text-center">
                  <svg className="animate-spin h-10 w-10 mx-auto mb-4 text-blue-500" viewBox="0 0 24 24" aria-hidden="true">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <p className="text-sm font-medium text-gray-600" aria-live="polite" aria-atomic="true">{step || "Processing..."}</p>
                  <div className="flex justify-center gap-1 mt-3" aria-hidden="true">
                    {PIPELINE_STEPS.map((s) => {
                      const currentIdx = step ? PIPELINE_STEPS.indexOf(step) : -1;
                      const stepIdx = PIPELINE_STEPS.indexOf(s);
                      const isDone = stepIdx < currentIdx;
                      const isCurrent = stepIdx === currentIdx;
                      return (
                        <div
                          key={s}
                          className={`h-1.5 w-6 rounded-full transition-colors ${
                            isDone ? "bg-green-400" : isCurrent ? "bg-blue-500" : "bg-gray-200"
                          }`}
                        />
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </ErrorBoundary>
        </div>
      </div>
    </main>
  );
}
