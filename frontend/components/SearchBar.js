import React from 'react';

const SearchBar = () => {
    return (
        <form action="/search" method="get" className="flex items-center">
            <input
                type="text"
                name="query"
                placeholder="Search pipelines..."
                className="px-4 py-2 border border-gray-300 rounded-l-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
                type="submit"
                className="px-4 py-2 bg-blue-500 text-white rounded-r-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
                Search
            </button>
        </form>
    );
};

export default SearchBar;
