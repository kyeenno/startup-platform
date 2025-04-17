export default function InputForm({
    label,
    type = 'text',
    id,
    placeholder,
    value,
    onChange,
    required = false,
    error
}) {
    return(
        <div>
            <label>
                {label}
            </label>
            <input 
                type={type}
                id={id}
                className="bg-gray-50 border border-gray-300 text-black text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
                placeholder={placeholder}
                value={value}
                onChange={onChange}
                required={required}
            />
            {error && <p className="text-sm">{error}</p>}
        </div>
    );
}