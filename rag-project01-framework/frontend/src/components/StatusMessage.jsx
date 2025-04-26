const StatusMessage = ({ status, type = 'info' }) => {
  const typeStyles = {
    error: 'bg-red-100 text-red-700',
    success: 'bg-green-100 text-green-700',
    warning: 'bg-yellow-100 text-yellow-700',
    info: 'bg-blue-100 text-blue-700'
  };

  return (
    <div className={`p-4 rounded-lg ${typeStyles[type]}`}>
      {status}
    </div>
  );
};

export default StatusMessage; 