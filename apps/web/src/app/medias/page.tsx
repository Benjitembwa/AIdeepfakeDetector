import type { Metadata } from "next";
import { MediaWorkspace } from "@/components/media-workspace";

export const metadata: Metadata = { title: "Espace média" };
export default function MediaPage() { return <MediaWorkspace />; }
