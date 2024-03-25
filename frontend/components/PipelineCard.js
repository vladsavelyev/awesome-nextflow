import React from 'react';
import styles from './PipelineCard.module.css';

const PipelineCard = ({pipeline}) => {
    return (
        <div className={styles.card}>
            <h3>{pipeline.title}</h3>
            <p>{pipeline.description}</p>
            <span>⭐ {pipeline.stars}</span>
            {/* You can add more details as per your design */}
        </div>
    );
};

export default PipelineCard;
