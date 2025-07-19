import axios from "axios";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL });

export const listAvatars = async () => (await api.get("/avatars")).data as { id:string;url:string }[];
export const listVoices  = async () => (await api.get("/voices")).data  as { id:string;lang:string }[];
export const startGenerate = async (body: { avatarId:string; voiceId:string; text:string; }) =>
  (await api.post("/assist", body)).data as { jobId:string };
