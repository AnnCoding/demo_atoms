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
  kind: "phase" | "delta" | "tool" | "coding" | "user" | "summary";
  text: string;
};

export type Approval = {
  artifact: string;
  value: string;
  sessionId: string;
};
