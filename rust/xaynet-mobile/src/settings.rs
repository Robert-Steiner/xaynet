//! This module provides utilities to configure a [`Participant`].
//!
//! [`Participant`]: crate::Participant

use std::convert::TryInto;
use thiserror::Error;
use xaynet_core::crypto::SigningKeyPair;
use xaynet_sdk::settings::{MaxMessageSize, PetSettings};

/// A participant settings
#[derive(Clone, Debug)]
pub struct Settings {
    /// The participant signing keys
    keys: Option<SigningKeyPair>,
    /// The Xaynet coordinator URL
    url: Option<String>,
    /// The scalar used for masking
    scalar: f64,
}

impl Default for Settings {
    fn default() -> Self {
        Self::new()
    }
}

impl Settings {
    /// Create new empty settings
    pub fn new() -> Self {
        Self {
            keys: None,
            url: None,
            scalar: 1.0,
        }
    }

    /// Set the participant signing keys
    pub fn set_keys(&mut self, keys: SigningKeyPair) {
        self.keys = Some(keys);
    }

    /// Set the scalar use for masking
    pub fn set_scalar(&mut self, scalar: f64) {
        self.scalar = scalar;
    }

    /// Set the Xaynet coordinator address
    pub fn set_url(&mut self, url: String) {
        self.url = Some(url);
    }

    /// Check whether the settings are complete and valid
    pub fn check(&self) -> Result<(), SettingsError> {
        if self.url.is_none() {
            Err(SettingsError::MissingUrl)
        } else if self.keys.is_none() {
            Err(SettingsError::MissingKeys)
        } else {
            Ok(())
        }
    }
}

/// Error returned when the settings are invalid
#[derive(Debug, Error)]
pub enum SettingsError {
    #[error("the Xaynet coordinator URL must be specified")]
    MissingUrl,
    #[error("the participant signing key pair must be specified")]
    MissingKeys,
}

impl TryInto<(String, PetSettings)> for Settings {
    type Error = SettingsError;

    fn try_into(self) -> Result<(String, PetSettings), Self::Error> {
        let Settings { keys, url, scalar } = self;

        let url = url.ok_or(SettingsError::MissingUrl)?;

        let keys = keys.ok_or(SettingsError::MissingKeys)?;

        let pet_settings = PetSettings {
            scalar,
            max_message_size: MaxMessageSize::default(),
            keys,
        };

        Ok((url, pet_settings))
    }
}
