import {NextPage} from 'next';
import {useRouter} from 'next/router';

interface Pipeline {
    id: string;
    title: string;
    description: string;
}

interface SearchResultsProps {
    pipelines: Pipeline[];
}

const SearchResults: NextPage<SearchResultsProps> = ({pipelines}) => {
    const router = useRouter();
    const {query} = router.query;

    // Render the search results
    return (
        <div>
            <h1>Search Results</h1>
            {/* Display the search results */}
            {pipelines.map((pipeline) => (
                <div key={pipeline.id}>
                    {/* Display pipeline details */}
                    <h2>{pipeline.title}</h2>
                    <p>{pipeline.description}</p>
                    {/* Add more pipeline details as needed */}
                </div>
            ))}
        </div>
    );
};

export async function getServerSideProps(context: any) {
    const {query} = context.query;

    // Fetch search results from the backend API
    const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/search?query=${encodeURIComponent(query)}`);
    const data = await res.json();

    return {
        props: {
            pipelines: data.results,
        },
    };
}

export default SearchResults;
