import { parseLabelText } from "./labelParser";

// OCR en el navegador. Se carga solo al usarlo porque pesa varios MB y descarga el idioma español.
export async function analyzeProductImage(image, onProgress = () => {}) {
  const { createWorker } = await import("tesseract.js");
  const worker = await createWorker("spa", 1, {
    logger: (message) => {
      if (message.status === "recognizing text") onProgress(Math.round(message.progress * 100));
    },
  });
  try {
    const { data } = await worker.recognize(image);
    return { ...parseLabelText(data.text), rawText: data.text.trim() };
  } finally {
    await worker.terminate();
  }
}
