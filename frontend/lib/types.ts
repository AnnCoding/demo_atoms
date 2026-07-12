export type AgentInfo = {
  id: string;
  name: string;
  role: string;
  emoji: string;
};

export type ModeInfo = {
  id: string;
  name: string;
  emoji: string;
  agents: string[];
  desc: string;
};

export type Msg = {
  id: number;
  agent: string;
  emoji: string;
  role: string;
  kind:
    | "phase"
    | "delta"
    | "tool"
    | "coding"
    | "user"
    | "summary"
    | "error"
    | "decision";
  text: string;
  payload?: Record<string, unknown>;
  timestamp?: string;
};

export type ChoiceOption = {
  id: string;
  label: string;
  description?: string;
  recommended?: boolean;
};

export type ClarifyQuestion = {
  id: string;
  question: string;
  type: "single_select" | "multi_select" | "text";
  required: boolean;
  options: ChoiceOption[];
  allow_custom: boolean;
};

export type ClarifyAnswers = Record<string, string | string[]>;

export type Approval = {
  artifact: string;
  value: string;
  sessionId: string;
};
