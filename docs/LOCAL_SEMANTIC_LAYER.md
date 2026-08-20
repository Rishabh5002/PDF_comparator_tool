# Local semantic matching layer

The comparison core now includes a dependency-free local vector similarity layer.
It builds TF-IDF vectors from word and character n-grams across the two sets of
questions and uses cosine similarity as an additional matching signal.

This is **not a generative LLM and is not a trained foundation model**. It is an
explainable local statistical representation. It requires no model download,
API key, network access, or document upload.

The matcher combines:

- normalized text similarity
- local vector similarity
- option similarity
- field-type similarity
- question-position similarity
- neighboring-question context

The local vector signal is deliberately only one part of the score. This keeps
matching auditable and prevents a generic textual similarity from overriding
strong structural evidence.

## Future extension

If evaluation on real company forms shows that statistical similarity is not
enough, a small pretrained embedding model can be added behind the same matcher
interface. Such a model would need to be packaged/downloaded ahead of time for
truly offline deployment. It would still be important to state that the model is
pretrained, not trained from scratch by this project.
