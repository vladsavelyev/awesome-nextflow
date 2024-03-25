import Image from "next/image";
import React from 'react';
import Head from 'next/head';
import Spotlight from '../components/Spotlight';


async function getSpotlightPipelines() {
    const res = await fetch('http://vladislavs-macbook-air.local:8001/spotlight')

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
            <br></br>
            <Spotlight pipelines={spotlightPipelines}/>
        </main>
    );
}
