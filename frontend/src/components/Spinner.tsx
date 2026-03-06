interface SpinnerProps {
  message?: string;
  subMessage?: string;
}

export default function Spinner({ message = 'Loading...', subMessage }: SpinnerProps) {
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 text-center">
        <div className="relative mx-auto w-20 h-20 mb-6">
          <div className="absolute inset-0 rounded-full border-4 border-primary-100"></div>
          <div className="absolute inset-0 rounded-full border-4 border-primary-600 border-t-transparent animate-spin"></div>
        </div>
        <h3 className="text-xl font-semibold text-gray-800 mb-2">{message}</h3>
        {subMessage && <p className="text-gray-500 text-sm">{subMessage}</p>}
      </div>
    </div>
  );
}
