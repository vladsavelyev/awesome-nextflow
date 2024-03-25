import React from 'react';
import PipelineCard from './PipelineCard';

const Spotlight = ({pipelines}) => {
    return (
        <div className="bg-white py-6 sm:py-8 lg:py-12">
            <div className="max-w-screen-2xl px-4 md:px-8 mx-auto">
                <h2 className="text-gray-800 text-2xl lg:text-3xl font-bold text-center mb-8 md:mb-12">Spotlight</h2>

                {/* Container for cards */}
                <div className="flex flex-wrap -mx-4">
                    {pipelines.map((pipeline) => (
                        <div className="w-full sm:w-1/2 lg:w-1/4 px-4"
                             key={pipeline.id}>
                            <PipelineCard pipeline={pipeline}/>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default Spotlight;
