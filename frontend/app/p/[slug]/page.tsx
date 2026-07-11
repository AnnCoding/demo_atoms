import { API } from "@/lib/api";
import ProjectViewer from "@/components/ProjectViewer";

type Msg = { role: string; agent: string; text: string };

export default async function SharePage({
  params,
}: {
  params: { slug: string };
}) {
  let code = "";
  let idea = "";
  let files: string[] = [];
  let conversation: Msg[] = [];
  try {
    const r = await fetch(`${API}/api/projects/${params.slug}`, {
      cache: "no-store",
    });
    const j = await r.json();
    code = j.project?.code || "";
    idea = j.project?.idea || "";
    files = j.project?.files || [];
    conversation = j.project?.conversation || [];
  } catch {
    code = "";
  }

  if (!code) {
    return (
      <div className="p-12 text-center text-gray-400">未找到该应用 😞</div>
    );
  }

  return (
    <ProjectViewer
      slug={params.slug}
      idea={idea}
      initialCode={code}
      files={files}
      conversation={conversation}
    />
  );
}
