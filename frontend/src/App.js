import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Table, Button, Modal, Badge } from 'react-bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';

function App() {
  const [data, setData] = useState([]);
  const [selectedRow, setSelectedRow] = useState(null);
  const [showUsageModal, setShowUsageModal] = useState(false);

  useEffect(() => {
    axios.get('http://127.0.0.1:8000/repositories')
      .then(response => {
        setData(response.data);
      });
  }, []);

  const handleCloseUsageModal = () => setShowUsageModal(false);
  const handleShowUsageModal = (row) => {
    setSelectedRow(row);
    setShowUsageModal(true);
  };

  return (

    <div className="container mt-4">
      <h1>Nextflow workflow catalog</h1>
      <Badge variant="secondary">{data.length}</Badge>
      <Table striped bordered hover>
        <thead>
          <tr>
            <th data-searchable="true" data-sortable="true" data-field="full_name" data-formatter="name_formatter">
                Workflow</th>
            <th data-field="usage" data-formatter="usage_formatter">&nbsp;</th>
            <th data-searchable="true" data-field="description">Description</th>
            <th data-searchable="true" data-field="topics" data-formatter="topics_formatter">Topics</th>
            <th data-sortable="true" data-field="stargazers_count" data_formatter="stargazers_formatter">Stars</th>
            <th data-sortable="true" data-field="subscribers_count" data_formatter="watchers_formatter">Watchers</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, index) => (
            <tr key={index}>
              <td><a href={`${row.url}`}>{row.title}</a></td>
              <td>
                {row.website &&
                  <Button variant="primary" onClick={() => handleShowUsageModal(row)}>Usage</Button>
                }
              </td>
              <td>{row.description}</td>
              <td>{row.topics}</td>
              <td>{row.stars}</td>
              <td>{row.watchers}</td>
            </tr>
          ))}
        </tbody>
      </Table>
      <Modal show={showUsageModal} onHide={handleCloseUsageModal}>
        <Modal.Header closeButton>
          <Modal.Title>Usage Information</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {/* You can add more details about the selected row here */}
          {selectedRow && (
            <div>
              <strong>Repository: </strong><a href={`${selectedRow.url}`}>{selectedRow.title}</a>
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleCloseUsageModal}>
            Close
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}

export default App;
