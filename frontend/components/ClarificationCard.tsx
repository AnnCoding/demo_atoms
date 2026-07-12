"use client";

import type { ClarifyAnswers, ClarifyQuestion } from "@/lib/types";

export default function ClarificationCard({
  questions,
  answers,
  onChange,
}: {
  questions: ClarifyQuestion[];
  answers: ClarifyAnswers;
  onChange: (answers: ClarifyAnswers) => void;
}) {
  const select = (question: ClarifyQuestion, optionId: string) => {
    if (question.type === "multi_select") {
      const current = Array.isArray(answers[question.id])
        ? (answers[question.id] as string[])
        : [];
      onChange({
        ...answers,
        [question.id]: current.includes(optionId)
          ? current.filter((item) => item !== optionId)
          : [...current, optionId],
      });
    } else {
      onChange({ ...answers, [question.id]: optionId });
    }
  };

  return (
    <div className="space-y-5">
      {questions.map((question, index) => {
        const selected = answers[question.id];
        return (
          <fieldset key={question.id} className="space-y-2">
            <legend className="text-sm font-semibold text-gray-900">
              {index + 1}. {question.question}
              {question.required && (
                <span className="text-red-500 ml-1">*</span>
              )}
            </legend>
            {question.options.length > 0 && (
              <div className="grid gap-2 sm:grid-cols-2">
                {question.options.map((option) => {
                  const checked = Array.isArray(selected)
                    ? selected.includes(option.id)
                    : selected === option.id;
                  return (
                    <button
                      type="button"
                      key={option.id}
                      onClick={() => select(question, option.id)}
                      className={`text-left rounded-lg border p-3 transition ${
                        checked
                          ? "border-blue-500 bg-blue-50 ring-1 ring-blue-300"
                          : "border-gray-200 hover:border-blue-300"
                      }`}
                    >
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <span
                          className={`h-4 w-4 ${question.type === "multi_select" ? "rounded" : "rounded-full"} border flex items-center justify-center ${checked ? "border-blue-600 bg-blue-600 text-white" : "border-gray-300"}`}
                        >
                          {checked ? "✓" : ""}
                        </span>
                        {option.label}
                        {option.recommended && (
                          <span className="text-[10px] rounded-full bg-emerald-100 px-2 py-0.5 text-emerald-700">
                            推荐
                          </span>
                        )}
                      </div>
                      {option.description && (
                        <div className="mt-1 pl-6 text-xs text-gray-500">
                          {option.description}
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
            {(question.type === "text" || question.allow_custom) && (
              <input
                value={(answers[`${question.id}__custom`] as string) || ""}
                onChange={(event) =>
                  onChange({
                    ...answers,
                    [`${question.id}__custom`]: event.target.value,
                    ...(question.type === "text"
                      ? { [question.id]: event.target.value }
                      : {}),
                  })
                }
                placeholder={
                  question.type === "text" ? "请输入答案" : "其他（可选）"
                }
                className="w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            )}
          </fieldset>
        );
      })}
    </div>
  );
}
