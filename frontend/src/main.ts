type VideoCreateResponse = {
  video_id: string;
  status: string;
};

type RoiFrame = {
  i: number;
  t_ms: number | null;
  x: number | null;
  y: number | null;
  w: number | null;
  h: number | null;
  score: number | null;
};

type RoiResponse = {
  video_id: string;
  fps: number | null;
  frames: RoiFrame[];
};

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Record<string, string> = {},
  children: (HTMLElement | string)[] = [],
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const child of children) node.append(child);
  return node;
}

function prettyJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}

async function uploadVideo(file: File): Promise<VideoCreateResponse> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch("/api/videos", { method: "POST", body: form });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Upload failed (${res.status}): ${text}`);
  }
  return (await res.json()) as VideoCreateResponse;
}

async function fetchRoi(videoId: string): Promise<RoiResponse> {
  const res = await fetch(`/api/videos/${videoId}/roi`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`ROI fetch failed (${res.status}): ${text}`);
  }
  return (await res.json()) as RoiResponse;
}

function buildUi() {
  const root = document.getElementById("app");
  if (!root) throw new Error("#app not found");

  const header = el("div", { style: "padding: 20px 20px 0 20px;" }, [
    el("h1", { style: "margin: 0; font-size: 20px;" }, ["Face ROI Demo"]),
    el("p", { style: "margin: 6px 0 0 0; opacity: 0.85;" }, [
      "Upload a short video; backend will return an annotated MP4 and per-frame ROI data.",
    ]),
  ]);

  const fileInput = el("input", { type: "file", accept: ".mp4,.webm,.mov,video/*" });
  const uploadBtn = el(
    "button",
    {
      style:
        "margin-left: 10px; padding: 8px 12px; border-radius: 8px; border: 0; background: #3b82f6; color: white; cursor: pointer;",
    },
    ["Upload"],
  );
  const status = el("div", { style: "margin-top: 12px; opacity: 0.9;" }, ["Idle."]);

  const video = el("video", {
    controls: "true",
    style: "width: 100%; max-height: 420px; background: black; border-radius: 12px; margin-top: 14px;",
  });

  const roiTitle = el("div", { style: "margin-top: 16px; font-weight: 600;" }, ["ROI JSON"]);
  const roiPre = el("pre", {
    style:
      "margin-top: 8px; padding: 12px; background: rgba(255,255,255,0.06); border-radius: 12px; overflow: auto; max-height: 300px;",
  });

  const panel = el("div", { style: "padding: 20px; max-width: 980px; margin: 0 auto;" }, [
    el("div", { style: "display: flex; align-items: center; gap: 10px; flex-wrap: wrap;" }, [
      fileInput,
      uploadBtn,
    ]),
    status,
    video,
    roiTitle,
    roiPre,
    el("div", { style: "margin-top: 10px; opacity: 0.7; font-size: 12px;" }, [
      "Tip: if the processed video doesn’t play in your browser, try a shorter MP4 clip.",
    ]),
  ]);

  let currentVideoId: string | null = null;

  uploadBtn.addEventListener("click", async () => {
    const file = fileInput.files?.[0];
    if (!file) {
      status.textContent = "Choose a video file first.";
      return;
    }

    uploadBtn.setAttribute("disabled", "true");
    uploadBtn.style.opacity = "0.7";
    status.textContent = "Uploading and processing… (this can take a bit)";
    roiPre.textContent = "";
    video.removeAttribute("src");

    try {
      const created = await uploadVideo(file);
      currentVideoId = created.video_id;
      status.textContent = `Done. video_id=${created.video_id} status=${created.status}`;

      // Serve annotated MP4 via backend endpoint.
      video.src = `/api/videos/${created.video_id}/stream`;

      const roi = await fetchRoi(created.video_id);
      roiPre.textContent = prettyJson(roi);
    } catch (e) {
      status.textContent = e instanceof Error ? e.message : String(e);
      currentVideoId = null;
    } finally {
      uploadBtn.removeAttribute("disabled");
      uploadBtn.style.opacity = "1";
    }
  });

  // tiny convenience: reload ROI if someone pasted a known id later
  void currentVideoId;

  root.append(header, panel);
}

buildUi();

