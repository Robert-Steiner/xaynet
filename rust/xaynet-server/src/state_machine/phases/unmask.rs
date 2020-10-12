use std::{cmp::Ordering, sync::Arc};

use xaynet_core::mask::{Aggregation, MaskObject, Model};

use crate::state_machine::{
    events::ModelUpdate,
    phases::{Idle, Phase, PhaseName, PhaseState, Shared, StateError},
    RoundFailed,
    StateMachine,
};

#[cfg(feature = "metrics")]
use crate::metrics;

/// Unmask state
#[derive(Debug)]
pub struct Unmask {
    /// The aggregator for masked models.
    model_agg: Option<Aggregation>,
}

#[cfg(test)]
impl Unmask {
    pub fn aggregation(&self) -> Option<&Aggregation> {
        self.model_agg.as_ref()
    }
}

#[async_trait]
impl Phase for PhaseState<Unmask> {
    const NAME: PhaseName = PhaseName::Unmask;

    /// Run the unmasking phase
    async fn run(&mut self) -> Result<(), StateError> {
        metrics!(
            self.shared.io.metrics_tx,
            metrics::masks::total_number::update(
                self.inner.model_mask_dict.len(),
                self.shared.state.round_id,
                Self::NAME
            )
        );

        let best_masks = self
            .shared
            .io
            .redis
            .connection()
            .await
            .get_best_masks()
            .await?;

        let global_model = self.end_round(best_masks).await?;

        info!("broadcasting the new global model");
        self.shared
            .io
            .events
            .broadcast_model(ModelUpdate::New(Arc::new(global_model)));

        Ok(())
    }

    /// Moves from the unmask state to the next state.
    ///
    /// See the [module level documentation](../index.html) for more details.
    fn next(self) -> Option<StateMachine> {
        info!("going back to idle phase");
        Some(PhaseState::<Idle>::new(self.shared).into())
    }
}

impl PhaseState<Unmask> {
    /// Creates a new unmask state.
    pub fn new(shared: Shared, model_agg: Aggregation) -> Self {
        info!("state transition");
        Self {
            inner: Unmask {
                model_agg: Some(model_agg),
            },
            shared,
        }
    }

    /// Freezes the mask dictionary.
    async fn freeze_mask_dict(
        &mut self,
        mut best_masks: Vec<(MaskObject, u64)>,
    ) -> Result<MaskObject, RoundFailed> {
        if best_masks.is_empty() {
            return Err(RoundFailed::NoMask);
        }

        let mask = best_masks
            .drain(0..)
            .fold(
                (None, 0),
                |(unique_mask, unique_count), (mask, count)| match unique_count.cmp(&count) {
                    Ordering::Less => (Some(mask), count),
                    Ordering::Greater => (unique_mask, unique_count),
                    Ordering::Equal => (None, unique_count),
                },
            )
            .0
            .ok_or(RoundFailed::AmbiguousMasks)?;

        Ok(mask)
    }

    async fn end_round(
        &mut self,
        best_masks: Vec<(MaskObject, u64)>,
    ) -> Result<Model, RoundFailed> {
        let mask = self.freeze_mask_dict(best_masks).await?;

        // Safe unwrap: State::<Unmask>::new always creates Some(aggregation)
        let model_agg = self.inner.model_agg.take().unwrap();

        model_agg
            .validate_unmasking(&mask)
            .map_err(RoundFailed::from)?;

        Ok(model_agg.unmask(mask))
    }
}
