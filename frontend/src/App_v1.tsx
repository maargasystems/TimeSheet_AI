import React, { useState } from 'react';
import './App.css';

interface AnalysisResult {
    result: any; // Change 'any' to your expected result type
}

const App: React.FC = () => {
    const [question, setQuestion] = useState<string>('');
    const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        
        try {
            const response = await fetch('http://localhost:8000/timesheetanalyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ question }),
            });

            if (!response.ok) {
                throw new Error(`Error: ${response.status} ${response.statusText}`);
            }

            const data: AnalysisResult = await response.json();
            setAnalysisResult(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Something went wrong');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="App">
            <h1>Timesheet Analysis</h1>
            <form onSubmit={handleSubmit}>
                <label htmlFor="question">Ask a question about timesheet data:</label>
                <input
                    type="text"
                    id="question"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    required
                />
                <button type="submit" disabled={loading}>
                    {loading ? 'Analyzing...' : 'Analyze'}
                </button>
            </form>

            {error && <p className="error">{error}</p>}
            {analysisResult && (
                <div>
                    <h2>Analysis Result</h2>
                    <pre>{JSON.stringify(analysisResult.result, null, 2)}</pre>
                </div>
            )}
        </div>
    );
};

export default App;