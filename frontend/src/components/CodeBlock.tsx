import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface CodeBlockProps {
  code: string;
  language?: string;
}

export default function CodeBlock({ code, language = 'python' }: CodeBlockProps) {
  if (!code) {
    return <p className="text-gray-500 italic">No code available.</p>;
  }

  return (
    <div className="rounded-lg overflow-hidden">
      <SyntaxHighlighter
        language={language}
        style={oneDark}
        showLineNumbers
        customStyle={{ margin: 0, borderRadius: '0.5rem', fontSize: '0.875rem' }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
