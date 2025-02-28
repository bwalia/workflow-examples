describe('smoke test', () => {
  it('Workstation Visit', () => {
      cy.visit('http://test-s3.workstation.co.uk/');
  })

  it('Workstation Visit', () => {
    cy.visit('https://s3.workstation.co.uk/');
  })

  it('Workstation Visit', () => {
    cy.visit('https://my.workstation.co.uk/');
  })

  it('Workstation Visit', () => {
    cy.visit('https://int-my.workstation.co.uk/');
  })

  it('Workstation Visit', () => {
    cy.visit('https://api-controlplane.brahmstra.org/');
  })

  it('Workstation Visit', () => {
    cy.visit('https://int-api-controlplane.brahmstra.org/');
  })

  it('Workstation Visit', () => {
    cy.visit('https://api-int.brahmstra.org/');
  })

  it('Workstation Visit', () => {
    cy.visit('https://es815.fictionally.xyz/');
  })

  it('Workstation Visit', () => {
    cy.visit('https://elastic.fictionally.xyz/');
  })

  it('Workstation Visit', () => {
    cy.visit('http://test.opsapi.io/');
  })

  it('Workstation Visit', () => {
    cy.visit('http://test-ui.opsapi.io/');
  })
})