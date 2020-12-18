use crate::from_primitives;
use crate::into_primitives;
use pyo3::create_exception;
use pyo3::exceptions::PyException;
use pyo3::types::PyList;
use pyo3::{prelude::*, wrap_pyfunction};
use xaynet_core::mask::IntoPrimitives;
use xaynet_core::mask::{DataType, FromPrimitives, Model};

use tracing::debug;
use tracing_subscriber::{EnvFilter, FmtSubscriber};

#[pymodule]
fn xaynet_sdk(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Participant>()?;
    m.add_function(wrap_pyfunction!(init_logging, m)?)?;
    m.add_function(wrap_pyfunction!(init_crypto, m)?)?;
    Ok(())
}

create_exception!(xaynet_sdk, CryptoInit, PyException);
create_exception!(xaynet_sdk, UninitializedParticipant, PyException);
create_exception!(xaynet_sdk, LocalModelLengthMisMatch, PyException);
create_exception!(xaynet_sdk, LocalModelDataTypeMisMatch, PyException);
create_exception!(xaynet_sdk, GlobalModelUnavailable, PyException);
create_exception!(xaynet_sdk, GlobalModelDataTypeMisMatch, PyException);

#[pyclass]
#[text_signature = "(url, scalar, /)"]
struct Participant {
    inner: Option<xaynet_mobile::Participant>,
}

#[pymethods]
impl Participant {
    #[new]
    pub fn new(url: String, scalar: f64) -> Self {
        let mut settings = xaynet_mobile::Settings::new();

        settings.set_keys(xaynet_core::crypto::SigningKeyPair::generate());
        settings.set_url(url);
        settings.set_scalar(scalar);

        let inner = xaynet_mobile::Participant::new(settings).unwrap();
        Self { inner: Some(inner) }
    }

    #[text_signature = "($self)"]
    pub fn tick(&mut self) -> PyResult<()> {
        let inner = match self.inner {
            Some(ref mut inner) => inner,
            None => {
                return Err(UninitializedParticipant::new_err(
                    "participant is uninitialized",
                ))
            }
        };

        inner.tick();
        Ok(())
    }

    #[text_signature = "($self, local_model)"]
    pub fn set_model(&mut self, local_model: &PyList) -> PyResult<()> {
        let inner = match self.inner {
            Some(ref mut inner) => inner,
            None => {
                return Err(UninitializedParticipant::new_err(
                    "participant is uninitialized",
                ))
            }
        };

        let local_model_config = inner.local_model_config();

        if local_model.len() != local_model_config.len {
            return Err(LocalModelLengthMisMatch::new_err(format!(
                "the local model length is incompatible with the model length of the current model configuration {} != {}",
                local_model.len(),
                local_model_config.len
            )));
        }

        debug!(
            "convert local model to {:?} datatype",
            local_model_config.data_type
        );

        match local_model_config.data_type {
            DataType::F32 => from_primitives!(inner, local_model, f32),
            DataType::F64 => from_primitives!(inner, local_model, f64),
            DataType::I32 => from_primitives!(inner, local_model, i32),
            DataType::I64 => from_primitives!(inner, local_model, i64),
        }
    }

    /// Check whether the participant internal state machine made progress while
    /// executing the PET protocol. If so, the participant state likely changed.
    #[text_signature = "($self)"]
    pub fn made_progress(&self) -> PyResult<bool> {
        let inner = match self.inner {
            Some(ref inner) => inner,
            None => {
                return Err(UninitializedParticipant::new_err(
                    "participant is uninitialized",
                ))
            }
        };

        Ok(inner.made_progress())
    }

    /// Check whether the participant internal state machine is waiting for the
    /// participant to load its model into the store. If this method returns `true`, the
    /// caller should make sure to call [`Participant::set_model()`] at some point.
    #[text_signature = "($self)"]
    pub fn should_set_model(&self) -> PyResult<bool> {
        let inner = match self.inner {
            Some(ref inner) => inner,
            None => {
                return Err(UninitializedParticipant::new_err(
                    "participant is uninitialized",
                ))
            }
        };

        Ok(inner.should_set_model())
    }

    #[text_signature = "($self)"]
    pub fn new_global_model(&self) -> PyResult<bool> {
        let inner = match self.inner {
            Some(ref inner) => inner,
            None => {
                return Err(UninitializedParticipant::new_err(
                    "participant is uninitialized",
                ))
            }
        };

        Ok(inner.new_global_model())
    }

    #[text_signature = "($self)"]
    pub fn global_model(&mut self, py: Python) -> PyResult<Option<Py<PyList>>> {
        let inner = match self.inner {
            Some(ref mut inner) => inner,
            None => {
                return Err(UninitializedParticipant::new_err(
                    "participant is uninitialized",
                ))
            }
        };

        let global_model = inner
            .global_model()
            .map_err(|_| GlobalModelUnavailable::new_err("failed to fetch global model"))?;

        let global_model = match global_model {
            Some(global_model) => global_model,
            None => return Ok(None),
        };

        match inner.local_model_config().data_type {
            DataType::F32 => into_primitives!(py, global_model, f32),
            DataType::F64 => into_primitives!(py, global_model, f64),
            DataType::I32 => into_primitives!(py, global_model, i32),
            DataType::I64 => into_primitives!(py, global_model, i64),
        }
    }

    #[text_signature = "($self)"]
    pub fn save(&mut self) -> PyResult<Vec<u8>> {
        let inner = match self.inner.take() {
            Some(inner) => inner,
            None => {
                return Err(UninitializedParticipant::new_err(
                    "participant is uninitialized",
                ))
            }
        };

        Ok(inner.save())
    }
}

#[macro_export]
macro_rules! into_primitives {
    ($py:expr, $global_model:expr, $data_type:ty) => {
        if let Ok(global_model) = $global_model
            .into_primitives()
            .collect::<Result<Vec<$data_type>, _>>()
        {
            let py_list = PyList::new($py, global_model.into_iter());
            Ok(Some(py_list.into()))
        } else {
            Err(GlobalModelDataTypeMisMatch::new_err(
                "the global model data type is incompatible with the data type of the current model configuration",
            ))
        }
    };
}

#[macro_export]
macro_rules! from_primitives {
    ($participant:expr, $local_model:expr, $data_type:ty) => {{
            let model: Vec<$data_type> = $local_model.extract()?;
            let converted_model = Model::from_primitives(model.into_iter());
            if let Ok(converted_model) = converted_model {
                $participant.set_model(converted_model);
                Ok(())
            } else {
                Err(LocalModelDataTypeMisMatch::new_err(
                    "the local model data type is incompatible with the data type of the current model configuration"
                ))
            }}
    };
}

#[pyfunction]
fn init_logging() {
    let env_filter = EnvFilter::try_from_env("XAYNET_CLIENT");
    if let Ok(filter) = env_filter {
        let _fmt_subscriber = FmtSubscriber::builder()
            .with_env_filter(filter)
            .with_ansi(true)
            .try_init();
    }
}

#[pyfunction]
fn init_crypto() -> PyResult<()> {
    sodiumoxide::init().map_err(|_| CryptoInit::new_err("failed to initialize crypto library"))
}
