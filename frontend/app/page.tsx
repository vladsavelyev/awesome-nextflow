import Image from "next/image";
import React from 'react';
import Spotlight from '../components/Spotlight';
import SearchBar from '../components/SearchBar';


async function getSpotlightPipelines() {
    // fetch data from backend api endpoint (the url is in .env file)
    const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/spotlight`)

    if (!res.ok) {
        throw new Error('Failed to fetch data')
    }

    return res.json()
}

export default async function Home() {
    const spotlightPipelines = await getSpotlightPipelines()

    return (
        <main className="flex flex-col items-center justify-between p-24">
            <div>
                <Image
                    src="/seqera_logo.png"
                    alt="Seqera Logo"
                    className="dark:invert"
                    width={100}
                    height={24}
                    priority
                />
            </div>
            <br/>
            <SearchBar/>
            <br/>
            <Spotlight pipelines={spotlightPipelines}/>
        </main>
    );
}
