use tracing::Span;

use crate::{
    state_machine::{
        events::DictionaryUpdate,
        phases::{self, PhaseState},
        requests::RequestSender,
        StateMachine,
        StateMachineResult,
    },
    storage::{CoordinatorStorage, ModelStorage},
};
use xaynet_core::message::Message;

impl RequestSender {
    pub async fn msg(&self, msg: &Message) -> StateMachineResult {
        self.request(msg.clone().into(), Span::none()).await
    }
}

impl<C, M> StateMachine<C, M>
where
    C: CoordinatorStorage,
    M: ModelStorage,
{
    pub fn is_update(&self) -> bool {
        matches!(self, StateMachine::Update(_))
    }

    pub fn into_update_phase_state(self) -> PhaseState<phases::Update, C, M> {
        match self {
            StateMachine::Update(state) => state,
            _ => panic!("not in update state"),
        }
    }

    pub fn is_sum(&self) -> bool {
        matches!(self, StateMachine::Sum(_))
    }

    pub fn into_sum_phase_state(self) -> PhaseState<phases::Sum, C, M> {
        match self {
            StateMachine::Sum(state) => state,
            _ => panic!("not in sum state"),
        }
    }

    pub fn is_sum2(&self) -> bool {
        matches!(self, StateMachine::Sum2(_))
    }

    pub fn into_sum2_phase_state(self) -> PhaseState<phases::Sum2, C, M> {
        match self {
            StateMachine::Sum2(state) => state,
            _ => panic!("not in sum2 state"),
        }
    }

    pub fn is_idle(&self) -> bool {
        matches!(self, StateMachine::Idle(_))
    }

    pub fn into_idle_phase_state(self) -> PhaseState<phases::Idle, C, M> {
        match self {
            StateMachine::Idle(state) => state,
            _ => panic!("not in idle state"),
        }
    }

    pub fn is_unmask(&self) -> bool {
        matches!(self, StateMachine::Unmask(_))
    }

    pub fn into_unmask_phase_state(self) -> PhaseState<phases::Unmask, C, M> {
        match self {
            StateMachine::Unmask(state) => state,
            _ => panic!("not in unmask state"),
        }
    }

    pub fn is_error(&self) -> bool {
        matches!(self, StateMachine::Error(_))
    }

    pub fn into_error_phase_state(self) -> PhaseState<phases::PhaseStateError, C, M> {
        match self {
            StateMachine::Error(state) => state,
            _ => panic!("not in error state"),
        }
    }

    pub fn is_shutdown(&self) -> bool {
        matches!(self, StateMachine::Shutdown(_))
    }

    pub fn into_shutdown_phase_state(self) -> PhaseState<phases::Shutdown, C, M> {
        match self {
            StateMachine::Shutdown(state) => state,
            _ => panic!("not in shutdown state"),
        }
    }
}

impl<D> DictionaryUpdate<D> {
    pub fn unwrap(self) -> std::sync::Arc<D> {
        if let DictionaryUpdate::New(inner) = self {
            inner
        } else {
            panic!("DictionaryUpdate::Invalidate");
        }
    }
}
