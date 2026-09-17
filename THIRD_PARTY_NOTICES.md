# Third-party data and service notices

PlantDoc preserves all package licences supplied by its dependencies. The application links to or consumes these external sources:

- **AGMARKNET / data.gov.in**: mandi data is published by the Directorate of Marketing and Inspection, Department of Agriculture and Farmers Welfare, Government of India, through the Open Government Data Platform under the Government Open Data License – India. PlantDoc displays the source and fetch timestamp and does not relabel modal price as an arithmetic average.
- **Open-Meteo**: weather forecasts and GeoNames-based geocoding are retrieved from Open-Meteo. The interface displays source and update information. Deployers must review Open-Meteo's current usage and attribution terms for their traffic level.
- **PlantDoc dataset**: the public PlantDoc field-image dataset by Singh et al. (2020) is licensed CC BY 4.0. The current experiment uses an explicit label mapping, separate validation and the official test split. Prior mapping/report limitations are documented in `docs/EVALUATION_REVIEW.md`.
- **PlantVillage**: the current experiment uses the official color-image archive and its 38-class convention, leaf identity groups, decoded-pixel hashes and near-duplicate grouping. Source images are not redistributed here; see the model audit for split sizes and limitations.
- **Wikimedia Commons**: commodity photographs are resolved at runtime through the Commons API. Each displayed image links to its source page and exposes the returned licence/credit metadata; images are not bundled or claimed as PlantDoc-owned.
- **Gemini API**: optional generated guidance is provided by Google's Gemini API when a private server credential is configured. Built-in guidance is clearly labelled when the provider is unavailable.

Dataset citations and links are maintained in `docs/MODEL_CARD.md`.

