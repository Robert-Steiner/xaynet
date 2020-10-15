//! Serialization of masked objects.
//!
//! See the [mask module] documentation since this is a private module anyways.
//!
//! [mask module]: ../index.html

pub(crate) mod vect;

use anyhow::Context;

use crate::{
    mask::object::{serialization::vect::MaskVectBuffer, MaskObject, MaskUnit, MaskVect},
    message::{
        traits::{FromBytes, ToBytes},
        DecodeError,
    },
};

// target dependent maximum number of mask object elements
#[cfg(target_pointer_width = "16")]
const MAX_NB: u32 = u16::MAX as u32;

/// A buffer for serialized mask objects.
pub struct MaskObjectBuffer<T> {
    inner: T,
}

impl<T: AsRef<[u8]>> MaskObjectBuffer<T> {
    /// Creates a new buffer from `bytes`.
    ///
    /// # Errors
    /// Fails if the `bytes` don't conform to the required buffer length for mask objects.
    pub fn new(bytes: T) -> Result<Self, DecodeError> {
        let buffer = Self { inner: bytes };
        buffer
            .check_buffer_length()
            .context("not a valid MaskObject")?;
        Ok(buffer)
    }

    /// Creates a new buffer from `bytes`.
    pub fn new_unchecked(bytes: T) -> Self {
        Self { inner: bytes }
    }

    /// Checks if this buffer conforms to the required buffer length for mask objects.
    ///
    /// # Errors
    /// Fails if the buffer is too small.
    pub fn check_buffer_length(&self) -> Result<(), DecodeError> {
        let inner = self.inner.as_ref();
        // check length of vector field
        MaskVectBuffer::new(&inner[0..]).context("invalid vector field")?;
        // check length of scalar field
        // TODO possible change to MaskOneBuffer in the future once implemented
        MaskVectBuffer::new(&inner[self.unit_offset()..]).context("invalid unit field")?;
        Ok(())
    }

    /// Gets the vector part.
    ///
    /// # Panics
    /// May panic if this buffer is unchecked.
    pub fn vect(&self) -> &[u8] {
        let len = self.unit_offset();
        &self.inner.as_ref()[0..len]
    }

    /// Gets the offset of the unit field.
    pub fn unit_offset(&self) -> usize {
        let vect_buf = MaskVectBuffer::new_unchecked(&self.inner.as_ref()[0..]);
        vect_buf.len()
    }

    /// Gets the unit part.
    ///
    /// # Panics
    /// May panic if this buffer is unchecked.
    pub fn unit(&self) -> &[u8] {
        let offset = self.unit_offset();
        &self.inner.as_ref()[offset..]
    }

    /// Gets the expected number of bytes of this buffer.
    ///
    /// # Panics
    /// May panic if this buffer is unchecked.
    pub fn len(&self) -> usize {
        let unit_offset = self.unit_offset();
        let unit_buf = MaskVectBuffer::new_unchecked(&self.inner.as_ref()[unit_offset..]);
        unit_offset + unit_buf.len()
    }
}

impl<T: AsRef<[u8]> + AsMut<[u8]>> MaskObjectBuffer<T> {
    /// Gets the vector part.
    ///
    /// # Panics
    /// May panic if this buffer is unchecked.
    pub fn vect_mut(&mut self) -> &mut [u8] {
        &mut self.inner.as_mut()[0..]
    }

    /// Gets the unit part.
    ///
    /// # Panics
    /// May panic if this buffer is unchecked.
    pub fn unit_mut(&mut self) -> &mut [u8] {
        let offset = self.unit_offset();
        &mut self.inner.as_mut()[offset..]
    }
}

impl ToBytes for MaskObject {
    fn buffer_length(&self) -> usize {
        self.vect.buffer_length() + self.unit.buffer_length()
    }

    fn to_bytes<T: AsMut<[u8]> + AsRef<[u8]>>(&self, buffer: &mut T) {
        let mut writer = MaskObjectBuffer::new_unchecked(buffer.as_mut());
        self.vect.to_bytes(&mut writer.vect_mut());
        self.unit.to_bytes(&mut writer.unit_mut());
    }
}

impl FromBytes for MaskObject {
    fn from_byte_slice<T: AsRef<[u8]>>(buffer: &T) -> Result<Self, DecodeError> {
        let reader = MaskObjectBuffer::new(buffer.as_ref())?;
        let vect = MaskVect::from_byte_slice(&reader.vect()).context("invalid vector part")?;
        let unit = MaskUnit::from_byte_slice(&reader.unit()).context("invalid unit part")?;
        Ok(Self { vect, unit })
    }

    fn from_byte_stream<I: Iterator<Item = u8> + ExactSizeIterator>(
        iter: &mut I,
    ) -> Result<Self, DecodeError> {
        let vect = MaskVect::from_byte_stream(iter).context("invalid vector part")?;
        let unit = MaskUnit::from_byte_stream(iter).context("invalid unit part")?;
        Ok(Self { vect, unit })
    }
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use crate::mask::{
        config::{BoundType, DataType, GroupType, MaskConfig, ModelType},
        MaskObject,
    };
    use num::BigUint;

    pub fn mask_config() -> (MaskConfig, Vec<u8>) {
        // config.order() = 20_000_000_000_001 with this config, so the data
        // should be stored on 6 bytes.
        let config = MaskConfig {
            group_type: GroupType::Integer,
            data_type: DataType::I32,
            bound_type: BoundType::B0,
            model_type: ModelType::M3,
        };
        let bytes = vec![0x00, 0x02, 0x00, 0x03];
        (config, bytes)
    }

    pub fn mask_vect() -> (MaskVect, Vec<u8>) {
        let (config, mut bytes) = mask_config();
        let data = vec![
            BigUint::from(1_u8),
            BigUint::from(2_u8),
            BigUint::from(3_u8),
            BigUint::from(4_u8),
        ];
        let mask_vect = MaskVect::new(config, data);

        bytes.extend(vec![
            // number of elements
            0x00, 0x00, 0x00, 0x04, // data (1 weight => 6 bytes with this config)
            0x01, 0x00, 0x00, 0x00, 0x00, 0x00, // 1
            0x02, 0x00, 0x00, 0x00, 0x00, 0x00, // 2
            0x03, 0x00, 0x00, 0x00, 0x00, 0x00, // 3
            0x04, 0x00, 0x00, 0x00, 0x00, 0x00, // 4
        ]);

        (mask_vect, bytes)
    }

    pub fn mask_unit() -> (MaskUnit, Vec<u8>) {
        let (config, mut bytes) = mask_config();
        let data = BigUint::from(1_u8);
        let mask_unit = MaskUnit::new(config, data);

        bytes.extend(vec![
            // number of elements
            0x00, 0x00, 0x00, 0x01, // data
            0x01, 0x00, 0x00, 0x00, 0x00, 0x00, // 1
        ]);
        (mask_unit, bytes)
    }

    pub fn mask_object() -> (MaskObject, Vec<u8>) {
        let (mask_vect, mask_vect_bytes) = mask_vect();
        let (mask_unit, mask_unit_bytes) = mask_unit();
        let obj = MaskObject::new(mask_vect, mask_unit);
        let bytes = [mask_vect_bytes.as_slice(), mask_unit_bytes.as_slice()].concat();

        (obj, bytes)
    }

    #[test]
    fn serialize_mask_object() {
        let (mask_object, expected) = mask_object();
        let mut buf = vec![0xff; 46];
        mask_object.to_bytes(&mut buf);
        assert_eq!(buf, expected);
    }

    #[test]
    fn deserialize_mask_object() {
        let (expected, bytes) = mask_object();
        assert_eq!(MaskObject::from_byte_slice(&&bytes[..]).unwrap(), expected);
    }

    #[test]
    fn deserialize_mask_object_from_stream() {
        let (expected, bytes) = mask_object();
        assert_eq!(
            MaskObject::from_byte_stream(&mut bytes.into_iter()).unwrap(),
            expected
        );
    }

    #[test]
    fn serialize_mask_vect() {
        let (mask_vect, expected) = mask_vect();
        let mut buf = vec![0xff; expected.len()];
        mask_vect.to_bytes(&mut buf);
        assert_eq!(buf, expected);
    }

    #[test]
    fn deserialize_mask_vect() {
        let (expected, bytes) = mask_vect();
        assert_eq!(MaskVect::from_byte_slice(&&bytes[..]).unwrap(), expected);
    }

    #[test]
    fn deserialize_mask_vect_from_stream() {
        let (expected, bytes) = mask_vect();
        assert_eq!(
            MaskVect::from_byte_stream(&mut bytes.into_iter()).unwrap(),
            expected
        );
    }

    #[test]
    fn serialize_mask_unit() {
        let (mask_unit, expected) = mask_unit();
        let mut buf = vec![0xff; expected.len()];
        mask_unit.to_bytes(&mut buf);
        assert_eq!(buf, expected);
    }

    #[test]
    fn deserialize_mask_unit() {
        let (expected, bytes) = mask_unit();
        assert_eq!(MaskUnit::from_byte_slice(&&bytes[..]).unwrap(), expected);
    }

    #[test]
    fn deserialize_mask_unit_from_stream() {
        let (expected, bytes) = mask_unit();
        assert_eq!(
            MaskUnit::from_byte_stream(&mut bytes.into_iter()).unwrap(),
            expected
        );
    }
}
