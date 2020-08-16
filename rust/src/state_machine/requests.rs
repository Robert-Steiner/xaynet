//! This module provides the the [`StateMachine`]'s `Request`, `RequestSender` and `RequestReceiver`
//! types.
//!
//! [`StateMachine`]: crate::state_machine::StateMachine
use std::{
    pin::Pin,
    task::{Context, Poll},
};

use derive_more::From;
use futures::Stream;
use thiserror::Error;
use tokio::sync::{mpsc, oneshot};
use tracing::Span;

/// Error that occurs when a [`RequestSender`] tries to send a request on a closed `Request` channel.
#[derive(Debug, Error)]
#[error("the RequestSender cannot be used because the state machine shut down")]
pub struct StateMachineShutdown;

use crate::{
    mask::object::MaskObject,
    message::{MessageOwned, PayloadOwned, UpdateOwned},
    state_machine::{StateMachineError, StateMachineResult},
    utils::{Request, Traceable},
    LocalSeedDict,
    ParticipantPublicKey,
    SumParticipantEphemeralPublicKey,
    SumParticipantPublicKey,
    UpdateParticipantPublicKey,
};

/// A sum request.
#[derive(Debug)]
pub struct SumRequest {
    /// The public key of the participant.
    pub participant_pk: SumParticipantPublicKey,
    /// The ephemeral public key of the participant.
    pub ephm_pk: SumParticipantEphemeralPublicKey,
}

/// An update request.
#[derive(Debug)]
pub struct UpdateRequest {
    /// The public key of the participant.
    pub participant_pk: UpdateParticipantPublicKey,
    /// The local seed dict that contains the seed used to mask `masked_model`.
    pub local_seed_dict: LocalSeedDict,
    /// The masked model trained by the participant.
    pub masked_model: MaskObject,
    /// The masked scalar used to scale model weights.
    pub masked_scalar: MaskObject,
}

/// A sum2 request.
#[derive(Debug)]
pub struct Sum2Request {
    /// The public key of the participant.
    pub participant_pk: ParticipantPublicKey,
    /// The model mask computed by the participant.
    pub model_mask: MaskObject,
    /// The scalar mask computed by the participant.
    pub scalar_mask: MaskObject
}

/// A [`StateMachine`] request.
///
/// [`StateMachine`]: crate::state_machine
#[derive(Debug, From)]
pub enum StateMachineRequest {
    Sum(SumRequest),
    Update(UpdateRequest),
    Sum2(Sum2Request),
}

impl Traceable for StateMachineRequest {
    fn make_span(&self) -> Span {
        let request_type = match self {
            Self::Sum(_) => "sum",
            Self::Update(_) => "update",
            Self::Sum2(_) => "sum2",
        };
        error_span!("StateMachineRequest", request_type = request_type)
    }
}

impl From<MessageOwned> for StateMachineRequest {
    fn from(message: MessageOwned) -> Self {
        let MessageOwned { header, payload } = message;
        match payload {
            PayloadOwned::Sum(sum) => StateMachineRequest::Sum(SumRequest {
                participant_pk: header.participant_pk,
                ephm_pk: sum.ephm_pk,
            }),
            PayloadOwned::Update(update) => {
                let UpdateOwned {
                    local_seed_dict,
                    masked_model,
                    masked_scalar,
                    ..
                } = update;
                StateMachineRequest::Update(UpdateRequest {
                    participant_pk: header.participant_pk,
                    local_seed_dict,
                    masked_model,
                    masked_scalar,
                })
            }
            PayloadOwned::Sum2(sum2) => StateMachineRequest::Sum2(Sum2Request {
                participant_pk: header.participant_pk,
                model_mask: sum2.model_mask,
                scalar_mask: sum2.scalar_mask,
            }),
        }
    }
}

/// A handle to send requests to the [`StateMachine`].
///
/// [`StateMachine`]: crate::state_machine
#[derive(Clone, From, Debug)]
pub struct RequestSender(mpsc::UnboundedSender<(Request<StateMachineRequest>, ResponseSender)>);

impl RequestSender {
    /// Sends a request to the [`StateMachine`].
    ///
    /// # Errors
    /// Fails if the [`StateMachine`] has already shut down and the `Request` channel has been
    /// closed as a result.
    ///
    /// [`StateMachine`]: crate::state_machine
    pub async fn request<T: Into<StateMachineRequest> + Traceable>(
        &self,
        req: Request<T>,
    ) -> StateMachineResult {
        let (resp_tx, resp_rx) = oneshot::channel::<StateMachineResult>();
        self.0.send((req.map(Into::into), resp_tx)).map_err(|_| {
            warn!("failed to send request to the state machine: state machine is shutting down");
            StateMachineError::InternalError
        })?;
        resp_rx.await.map_err(|_| {
            warn!(
                "failed to receive response from the state machine: state machine is shutting down"
            );
            StateMachineError::InternalError
        })?
    }
}

/// A channel for sending the state machine to send the response to a
/// [`StateMachineRequest`].
pub(in crate::state_machine) type ResponseSender = oneshot::Sender<StateMachineResult>;

/// The receiver half of the `Request` channel that is used by the [`StateMachine`] to receive
/// requests.
///
/// [`StateMachine`]: crate::state_machine
#[derive(From, Debug)]
pub struct RequestReceiver(mpsc::UnboundedReceiver<(Request<StateMachineRequest>, ResponseSender)>);

impl Stream for RequestReceiver {
    type Item = (Request<StateMachineRequest>, ResponseSender);

    fn poll_next(self: Pin<&mut Self>, cx: &mut Context) -> Poll<Option<Self::Item>> {
        trace!("RequestReceiver: polling");
        Pin::new(&mut self.get_mut().0).poll_next(cx)
    }
}

impl RequestReceiver {
    /// Creates a new `Request` channel and returns the [`RequestReceiver`] as well as the
    /// [`RequestSender`] half.
    pub fn new() -> (Self, RequestSender) {
        let (tx, rx) = mpsc::unbounded_channel::<(Request<StateMachineRequest>, ResponseSender)>();
        let receiver = RequestReceiver::from(rx);
        let handle = RequestSender::from(tx);
        (receiver, handle)
    }

    /// Closes the `Request` channel.
    /// See [the `tokio` documentation][close] for more information.
    ///
    /// [close]: https://docs.rs/tokio/0.2.21/tokio/sync/mpsc/struct.UnboundedReceiver.html#method.close
    pub fn close(&mut self) {
        self.0.close()
    }

    /// Receives the next request.
    /// See [the `tokio` documentation][receive] for more information.
    ///
    /// [receive]: https://docs.rs/tokio/0.2.21/tokio/sync/mpsc/struct.UnboundedReceiver.html#method.recv
    pub async fn recv(&mut self) -> Option<(Request<StateMachineRequest>, ResponseSender)> {
        self.0.recv().await
    }

    /// Try to retrieve the next request without blocked
    /// See [the `tokio` documentation][try_receive] for more information.
    ///
    /// [try_receive]: https://docs.rs/tokio/0.2.21/tokio/sync/mpsc/struct.UnboundedReceiver.html#method.try_recv
    pub fn try_recv(
        &mut self,
    ) -> Result<
        (Request<StateMachineRequest>, ResponseSender),
        tokio::sync::mpsc::error::TryRecvError,
    > {
        self.0.try_recv()
    }
}
