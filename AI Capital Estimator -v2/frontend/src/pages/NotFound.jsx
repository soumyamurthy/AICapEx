import { Link } from "react-router-dom";

export default function NotFound() {
    return (
        <div className="page">
            <header className="page-header">
                <h1>Page not found</h1>
                <p className="subtitle">
                    The page you are looking for does not exist. <Link to="/">Go back home.</Link>
                </p>
            </header>
        </div>
    );
}
