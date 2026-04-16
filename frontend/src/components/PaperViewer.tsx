import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface PaperViewerProps {
  markdown: string;
}

export default function PaperViewer({ markdown }: PaperViewerProps) {
  if (!markdown) {
    return <p className="text-[#aaabb0] italic">No paper content available.</p>;
  }

  return (
    <div className="prose prose-invert max-w-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
    </div>
  );
}
