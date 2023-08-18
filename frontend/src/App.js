import './App.css';
import React, {useEffect, useState} from "react";

function App() {
    const [data, setData] = useState([]);

    useEffect(() => {
        fetch('http://127.0.0.1:8000/repositories')
            .then(response => response.json())
            .then(data => setData(data));
    }, []);

    return (
        <div className="App">
            <table>
                <caption>Nextflow awesome workflows</caption>
                <thead>
                <tr>
                    <th>URL</th>
                    <th>Title</th>
                    <th>Description</th>
                </tr>
                </thead>
                <tbody>
                {data.map((repo) => (
                    <tr key={repo.id}>
                        <td><a href={repo.url}>{repo.url}</a></td>
                        <td>{repo.title}</td>
                        <td>{repo.description}</td>
                    </tr>
                ))}
                </tbody>
            </table>
        </div>
    )
}

export default App;
