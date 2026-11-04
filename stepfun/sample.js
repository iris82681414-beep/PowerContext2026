export const documents = [
  ['Bread cooling', 'After baking a sourdough loaf, move it to a wire rack. Wait until the center has cooled before slicing. Airflow around the bottom prevents a soft crust.'],
  ['Plant watering', 'Check the soil with a finger before watering a houseplant. Drain excess water from the pot saucer to prevent the roots sitting in water.'],
  ['Bike chain care', 'Wipe dirt from the chain with a cloth. Apply a drop of chain lubricant to each roller, then remove excess oil. Do not spray lubricant on brake rotors.'],
  ['Paper references', 'Record the authors, year, title, venue, and stable identifier when saving a paper. Keep a page reference for every quotation.'],
  ['Laptop battery care', 'Store a laptop in a cool dry place. For extended storage, leave its battery partially charged and check it periodically.'],
  ['Tea steeping', 'Use water below boiling for delicate green tea leaves. A shorter infusion can reduce bitterness. Taste before extending the steep.'],
  ['PostgreSQL backups', 'Test database backups by restoring them into a separate instance. Compare row counts and run important read queries before trusting recovery.'],
  ['Road trip packing', 'Keep a flashlight, water, a charging cable, and a first aid kit in an accessible bag. Store heavy luggage low in the vehicle.'],
  ['Dataset splits', 'Assign all records from the same person to one dataset split. Grouping prevents training records from leaking into the evaluation set.'],
  ['Pottery drying', 'Dry a clay pot slowly and evenly under a loose cover. Let it become completely dry before firing to reduce the chance of cracking.'],
  ['Window cleaning', 'Use a squeegee after washing window glass. Wipe the blade between strokes and dry the edges with a clean cloth.'],
  ['Conference notes', 'Keep meeting decisions separate from open questions. Record an owner and due date for every agreed action.'],
].map(([title, text]) => ({ title, text }));

export const queries = [
  ['How do I let a baked loaf cool before cutting it?', 'Bread cooling'],
  ['How do I check a database backup actually works?', 'PostgreSQL backups'],
  ['What information should I save when citing a research article?', 'Paper references'],
  ['How can I keep the training and evaluation sets independent for each person?', 'Dataset splits'],
  ['How do I reduce green tea bitterness?', 'Tea steeping'],
  ['How do I keep a clay vessel from cracking as it dries?', 'Pottery drying'],
].map(([query, expectedTitle]) => ({ query, expectedTitle }));
