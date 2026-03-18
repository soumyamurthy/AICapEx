export default function Loading({ message = "Loading..." }) {
    return (
        <div className="loading">
            <div className="loading__spinner" aria-hidden="true" />
            <div className="loading__message">{message}</div>
        </div>
    );
}
