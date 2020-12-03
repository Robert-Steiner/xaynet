use pyo3::{exceptions, prelude::*, wrap_pyfunction};
use xaynet_core::mask::{FromPrimitives, Model};

use tracing_subscriber::{EnvFilter, FmtSubscriber};

#[pymodule]
fn xaynet_sdk(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Participant>()?;
    m.add_function(wrap_pyfunction!(enable_logging, m)?)?;
    m.add_function(wrap_pyfunction!(init_crypto, m)?)?;
    Ok(())
}

#[pyclass]
struct Participant {
    inner: Option<xaynet_mobile::Participant>,
}

#[pymethods]
impl Participant {
    #[new]
    fn new(url: String) -> Self {
        let mut settings = xaynet_mobile::Settings::new();

        settings.set_keys(xaynet_core::crypto::SigningKeyPair::generate());
        settings.set_url(url);
        settings.set_scalar(1.0);

        let inner = xaynet_mobile::Participant::new(settings).unwrap();
        Self { inner: Some(inner) }
    }

    fn tick(&mut self) -> PyResult<()> {
        if let Some(ref mut inner) = self.inner {
            inner.tick();
        }
        Ok(())
    }

    fn set_model(&mut self, model: Vec<f32>) -> PyResult<()> {
        if let Some(ref mut inner) = self.inner {
            inner.set_model(Model::from_primitives(model.into_iter()).unwrap());
        }
        Ok(())
    }

    /// Check whether the participant internal state machine made progress while
    /// executing the PET protocol. If so, the participant state likely changed.
    pub fn made_progress(&self) -> PyResult<bool> {
        if let Some(ref inner) = self.inner {
            return Ok(inner.made_progress());
        }
        Err(exceptions::PyTypeError::new_err("No participant"))
    }

    /// Check whether the participant internal state machine is waiting for the
    /// participant to load its model into the store. If this method returns `true`, the
    /// caller should make sure to call [`Participant::set_model()`] at some point.
    pub fn should_set_model(&self) -> PyResult<bool> {
        if let Some(ref inner) = self.inner {
            return Ok(inner.should_set_model());
        }
        Err(exceptions::PyTypeError::new_err("No participant"))
    }

    // /// Return the participant current task
    // pub fn task(&self) -> PyResult<xaynet_mobile::Task> {
    //     if let Some(ref inner) = self.inner {
    //         return Ok(inner.task());
    //     }
    //     Err(exceptions::PyTypeError::new_err("No participant"))
    // }

    fn save(&mut self) -> PyResult<Vec<u8>> {
        if let Some(inner) = self.inner.take() {
            return Ok(inner.save());
        }
        Err(exceptions::PyTypeError::new_err("No participant"))
    }
}

#[pyfunction]
fn enable_logging() {
    let env_filter = EnvFilter::try_from_env("XAYNET_CLIENT");
    if env_filter.is_ok() {
        let _fmt_subscriber = FmtSubscriber::builder()
            .with_env_filter(env_filter.unwrap())
            .with_ansi(true)
            .try_init();
    }
}

#[pyfunction]
fn init_crypto() {
    sodiumoxide::init().unwrap()
}
