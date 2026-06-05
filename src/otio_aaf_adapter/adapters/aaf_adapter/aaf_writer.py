# SPDX-License-Identifier: Apache-2.0
# Copyright Contributors to the OpenTimelineIO project

"""AAF Adapter Transcriber

Specifies how to transcribe an OpenTimelineIO file into an AAF file.
"""

from numbers import Rational

import aaf2
import abc
import uuid
import opentimelineio as otio
import os
import copy
import re
import logging

AAF_PARAMETERDEF_PAN = aaf2.auid.AUID("e4962322-2267-11d3-8a4c-0050040ef7d2")
AAF_OPERATIONDEF_MONOAUDIOPAN = aaf2.auid.AUID("9d2ea893-0968-11d3-8a38-0050040ef7d2")
AAF_PARAMETERDEF_AVIDPARAMETERBYTEORDER = uuid.UUID(
    "c0038672-a8cf-11d3-a05b-006094eb75cb"
)
AAF_PARAMETERDEF_AVIDEFFECTID = uuid.UUID("93994bd6-a81d-11d3-a05b-006094eb75cb")
AAF_PARAMETERDEF_AFX_FG_KEY_OPACITY_U = uuid.UUID(
    "8d56813d-847e-11d5-935a-50f857c10000"
)
AAF_PARAMETERDEF_LEVEL = uuid.UUID("e4962320-2267-11d3-8a4c-0050040ef7d2")
# Audio Gain uses "Amplitude" ParameterDef (matching DaVinci Resolve)
AAF_PARAMETERDEF_AMPLITUDE = uuid.UUID("e4962321-2267-11d3-8a4c-0050040ef7d2")
AAF_VVAL_EXTRAPOLATION_ID = uuid.UUID("0e24dd54-66cd-4f1a-b0a0-670ac3a7a0b3")
AAF_OPERATIONDEF_SUBMASTER = uuid.UUID("f1db0f3d-8d64-11d3-80df-006008143e6f")
# Audio Gain OperationDefinition (AAF standard MonoAudioGain, matching DaVinci Resolve)
AAF_OPERATIONDEF_AUDIOGAIN = uuid.UUID("9d2ea894-0968-11d3-8a38-0050040ef7d2")

logger = logging.getLogger(__name__)


def _is_considered_gap(thing):
    """Returns whether or not thiing can be considered gap.

    TODO: turns generators w/ kind "Slug" inito gap.  Should probably generate
          opaque black instead.
    """
    if isinstance(thing, otio.schema.Gap):
        return True

    if isinstance(thing, otio.schema.Clip) and isinstance(
        thing.media_reference, otio.schema.GeneratorReference
    ):
        if thing.media_reference.generator_kind in ("Slug",):
            return True
        else:
            raise otio.exceptions.NotSupportedError(
                "AAF adapter does not support generator references of kind"
                " '{}'".format(thing.media_reference.generator_kind)
            )

    return False


def _nearest_timecode(rate):
    supported_rates = (24.0, 25.0, 30.0, 60.0)
    nearest_rate = 0.0
    min_diff = float("inf")
    for valid_rate in supported_rates:
        if valid_rate == rate:
            return rate

        diff = abs(rate - valid_rate)
        if diff >= min_diff:
            continue

        min_diff = diff
        nearest_rate = valid_rate

    return nearest_rate


class AAFAdapterError(otio.exceptions.OTIOError):
    pass


class AAFValidationError(AAFAdapterError):
    pass


def _patch_mob_id_prefix(mob):
    """Rewrite MobID bytes 8-11 from pyaaf2 default to DaVinci Resolve.

    Changes bytes 8-11 from 01010f20 to 01010d43.
    """
    mid = mob.mob_id
    mid.bytes_le[8] = 0x01
    mid.bytes_le[9] = 0x01
    mid.bytes_le[10] = 0x0d
    mid.bytes_le[11] = 0x43
    mob.mob_id = mid


class AAFFileTranscriber:
    """
    AAFFileTranscriber

    AAFFileTranscriber manages the file-level knowledge during a conversion from
    otio to aaf. This includes keeping track of unique tapemobs and mastermobs.
    """

    def __init__(self, input_otio, aaf_file, **kwargs):
        """
        AAFFileTranscriber requires an input timeline and an output pyaaf2 file handle.

        Args:
            input_otio: an input OpenTimelineIO timeline
            aaf_file: a pyaaf2 file handle to an output file
        """
        self.aaf_file = aaf_file
        self.compositionmob = self.aaf_file.create.CompositionMob()
        # Use timeline name if available, otherwise use a default name
        self.compositionmob.name = input_otio.name if input_otio.name else "Timeline 1"
        self.compositionmob.usage = "Usage_TopLevel"

        # Set CompositionMob MobID to match DaVinci Resolve format
        # Resolve uses: 060a2b34.01010101.01010f00.13000000.{unique}
        import uuid
        unique_part = uuid.uuid4().hex
        # Format: 060a2b34-0101-0101-0101-0f0013000000 + 32 hex chars
        new_mob_id = aaf2.mobid.MobID(
            f"060a2b34-0101-0101-0101-0f0013000000-{unique_part}"
        )
        self.compositionmob.mob_id = new_mob_id

        # Don't append CompositionMob yet - add all mobs in correct order
        # at the end
        self._unique_mastermobs = {}
        self._unique_tapemobs = {}
        self._filemobs = {}  # Store filemobs (WAVEDescriptor) separately
        self._clip_mob_ids_map = _gather_clip_mob_ids(input_otio, **kwargs)
        self._mobs_to_append = []  # Track mobs to append in order

        # transcribe timeline comments onto composition mob
        self._transcribe_user_comments(input_otio, self.compositionmob)

    def append_all_mobs(self):
        """
        Append all mobs to the AAF file in the correct order.
        DaVinci Resolve interleaves mobs per clip:
        CompositionMob, [MasterMob, TapeMob, FileMob],
        [MasterMob, TapeMob, FileMob], ...
        """
        # 1. CompositionMob first
        self.aaf_file.content.mobs.append(self.compositionmob)

        # 2. Append mobs in insertion order (master, tape, file per clip)
        for mob_type, mob in self._mobs_to_append:
            self.aaf_file.content.mobs.append(mob)

    def _unique_mastermob(self, otio_clip):
        """Get a unique mastermob, identified by clip metadata mob id."""
        mob_id = self._clip_mob_ids_map.get(otio_clip)
        mastermob = self._unique_mastermobs.get(mob_id)
        if not mastermob:
            mastermob = self.aaf_file.create.MasterMob()
            mastermob.name = otio_clip.name
            mastermob.mob_id = aaf2.mobid.MobID(mob_id)
            _patch_mob_id_prefix(mastermob)
            self._unique_mastermobs[mob_id] = mastermob

            # transcribe clip comments onto master mob
            self._transcribe_user_comments(otio_clip, mastermob)

            # transcribe media reference comments onto master mob.
            # this might overwrite clip comments.
            self._transcribe_user_comments(otio_clip.media_reference, mastermob)

        return mastermob

    def _unique_tapemob(self, otio_clip):
        """Get a unique tapemob with TapeDescriptor.

        Identified by clip metadata mob id.
        """
        mob_id = self._clip_mob_ids_map.get(otio_clip)
        tapemob = self._unique_tapemobs.get(mob_id)
        if not tapemob:
            tapemob = self.aaf_file.create.SourceMob()
            tapemob.name = ""  # TapeDescriptor SourceMob has empty name
            tapemob.descriptor = self.aaf_file.create.TapeDescriptor()
            _patch_mob_id_prefix(tapemob)
            self._unique_tapemobs[mob_id] = tapemob

            # If the edit_rate is not an integer, we need
            # to use drop frame with a nominal integer fps.
            edit_rate = otio_clip.visible_range().duration.rate
            timecode_fps = round(edit_rate)
            tape_timecode_slot = tapemob.create_timecode_slot(
                edit_rate=edit_rate,
                timecode_fps=timecode_fps,
                drop_frame=(edit_rate != timecode_fps),
            )
            timecode_start = int(
                otio_clip.media_reference.available_range.start_time.value
            )
            timecode_length = int(
                otio_clip.media_reference.available_range.duration.value
            )

            tape_timecode_slot.segment.start = int(timecode_start)
            tape_timecode_slot.segment.length = int(timecode_length)
            tape_timecode_slot["PhysicalTrackNumber"].value = 1

        return tapemob

    def track_transcriber(self, otio_track):
        """Return an appropriate _TrackTranscriber given an otio track.
        Results are cached to avoid duplicate mobslot creation."""
        if not hasattr(self, '_transcriber_cache'):
            self._transcriber_cache = {}

        track_id = id(otio_track)
        if track_id in self._transcriber_cache:
            return self._transcriber_cache[track_id]

        if otio_track.kind == otio.schema.TrackKind.Video:
            transcriber = VideoTrackTranscriber(self, otio_track)
        elif otio_track.kind == otio.schema.TrackKind.Audio:
            transcriber = AudioTrackTranscriber(self, otio_track)
        else:
            raise otio.exceptions.NotSupportedError(
                f"Unsupported track kind: {otio_track.kind}"
            )

        self._transcriber_cache[track_id] = transcriber
        return transcriber

    def add_timecode_first(self, input_otio, default_edit_rate):
        """
        Add CompositionMob level timecode track as the FIRST slot (SlotID=1).
        This is required for compatibility with Pro Tools and DaVinci Resolve.
        """
        if input_otio.global_start_time:
            edit_rate = input_otio.global_start_time.rate
            start = int(input_otio.global_start_time.value)
        else:
            edit_rate = default_edit_rate
            start = 0

        # Calculate timecode length based on timeline duration
        # +1 to match DaVinci Resolve's behavior (inclusive end frame)
        timeline_duration = input_otio.duration()
        timecode_length = int(timeline_duration.value) + 1

        # Create the timecode slot with SlotID=1 (first slot)
        slot = self.compositionmob.create_timeline_slot(edit_rate, slot_id=1)
        slot.name = ""

        # indicated that this is the primary timecode track
        slot["PhysicalTrackNumber"].value = 1

        # timecode.start is in edit_rate units NOT timecode fps
        timecode = self.aaf_file.create.Timecode()
        timecode.fps = int(_nearest_timecode(edit_rate))
        timecode.drop = False
        timecode.start = start
        timecode.length = timecode_length
        slot.segment = timecode

    def add_timecode(self, input_otio, default_edit_rate):
        """
        Add CompositionMob level timecode track.

        Deprecated - use add_timecode_first instead.
        """
        # For backward compatibility, just call add_timecode_first
        self.add_timecode_first(input_otio, default_edit_rate)

    def _transcribe_user_comments(self, otio_item, target_mob):
        """Transcribes user comments on `otio_item` onto `target_mob` in AAF."""

        user_comments = otio_item.metadata.get("AAF", {}).get("UserComments", {})
        for key, val in user_comments.items():
            if isinstance(val, (int, str)):
                target_mob.comments[key] = val
            elif isinstance(val, (float, Rational)):
                target_mob.comments[key] = aaf2.rational.AAFRational(val)
            else:
                logger.warning(
                    f"Skip transcribing unsupported comment value of type "
                    f"'{type(val)}' for key '{key}'."
                )


def validate_metadata(timeline):
    """Print a check of necessary metadata requirements for an otio timeline."""

    all_checks = [__check(timeline, "duration().rate")]
    edit_rate = __check(timeline, "duration().rate").value

    for child in timeline.find_children():
        checks = []
        if _is_considered_gap(child):
            checks = [__check(child, "duration().rate").equals(edit_rate)]
        if isinstance(child, otio.schema.Clip):
            checks = [
                __check(child, "duration().rate").equals(edit_rate),
                __check(child, "media_reference.available_range.duration.rate").equals(
                    edit_rate
                ),
                __check(
                    child, "media_reference.available_range.start_time.rate"
                ).equals(edit_rate),
            ]
        if isinstance(child, otio.schema.Transition):
            checks = [
                __check(child, "duration().rate").equals(edit_rate),
                __check(child, "metadata['AAF']['PointList']"),
                __check(
                    child,
                    "metadata['AAF']['OperationGroup']['Operation']"
                    "['DataDefinition']['Name']",
                ),
                __check(
                    child,
                    "metadata['AAF']['OperationGroup']['Operation']" "['Description']",
                ),
                __check(
                    child, "metadata['AAF']['OperationGroup']['Operation']" "['Name']"
                ),
                __check(child, "metadata['AAF']['CutPoint']"),
            ]
        all_checks.extend(checks)

    if any(check.errors for check in all_checks):
        raise AAFValidationError(
            "\n" + "\n".join(sum([check.errors for check in all_checks], []))
        )


def _gather_clip_mob_ids(
    input_otio, prefer_file_mob_id=False, use_empty_mob_ids=False, **kwargs
):
    """
    Create dictionary of otio clips with their corresponding mob ids.
    """

    def _from_clip_metadata(clip):
        """Get the MobID from the clip.metadata."""
        return clip.metadata.get("AAF", {}).get("SourceID")

    def _from_media_reference_metadata(clip):
        """Get the MobID from the media_reference.metadata."""
        return clip.media_reference.metadata.get("AAF", {}).get(
            "MobID"
        ) or clip.media_reference.metadata.get("AAF", {}).get("SourceID")

    def _from_aaf_file(clip):
        """Get the MobID from the AAF file itself."""
        mob_id = None
        if isinstance(clip.media_reference, otio.schema.ExternalReference):
            target_url = clip.media_reference.target_url
            if os.path.isfile(target_url) and target_url.endswith("aaf"):
                with aaf2.open(clip.media_reference.target_url) as aaf_file:
                    mastermobs = list(aaf_file.content.mastermobs())
                    if len(mastermobs) == 1:
                        mob_id = mastermobs[0].mob_id
        return mob_id

    def _generate_empty_mobid(clip):
        """Generate a meaningless MobID."""
        return aaf2.mobid.MobID.new()

    strategies = [
        _from_clip_metadata,
        _from_media_reference_metadata,
        _from_aaf_file,
        _generate_empty_mobid,
    ]

    if prefer_file_mob_id:
        strategies.remove(_from_aaf_file)
        strategies.insert(0, _from_aaf_file)

    if use_empty_mob_ids:
        strategies.append(_generate_empty_mobid)

    clip_mob_ids = {}

    for otio_clip in input_otio.find_clips():
        if _is_considered_gap(otio_clip):
            continue
        for strategy in strategies:
            mob_id = strategy(otio_clip)
            if mob_id:
                clip_mob_ids[otio_clip] = mob_id
                break
        else:
            raise AAFAdapterError(f"Cannot find mob ID for clip {otio_clip}")

    return clip_mob_ids


def _stackify_nested_groups(timeline):
    """
    Ensure that all nesting in a given timeline is in a stack container.
    This conforms with how AAF thinks about nesting, there needs
    to be an outer container, even if it's just one object.
    """
    copied = copy.deepcopy(timeline)
    for track in copied.tracks:
        for i, child in enumerate(track.find_children()):
            is_nested = isinstance(child, otio.schema.Track)
            is_parent_in_stack = isinstance(child.parent(), otio.schema.Stack)
            if is_nested and not is_parent_in_stack:
                stack = otio.schema.Stack()
                track.remove(child)
                stack.append(child)
                track.insert(i, stack)
    return copied


class _TrackTranscriber:
    """
    _TrackTranscriber is the base class for the conversion of a given otio track.

    _TrackTranscriber is not meant to be used by itself. It provides the common
    functionality to inherit from. We need an abstract base class because Audio and
    Video are handled differently.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, root_file_transcriber, otio_track):
        """
        _TrackTranscriber

        Args:
            root_file_transcriber: the corresponding 'parent' AAFFileTranscriber object
            otio_track: the given otio_track to convert
        """
        self.root_file_transcriber = root_file_transcriber
        self.compositionmob = root_file_transcriber.compositionmob
        self.aaf_file = root_file_transcriber.aaf_file
        self.otio_track = otio_track
        self.edit_rate = self.otio_track.find_children()[0].duration().rate
        self.timeline_mobslot, self.sequence = self._create_timeline_mobslot()
        self.timeline_mobslot.name = self.otio_track.name

    def transcribe(self, otio_child):
        """Transcribe otio child to corresponding AAF object"""
        if _is_considered_gap(otio_child):
            filler = self.aaf_filler(otio_child)
            return filler
        elif isinstance(otio_child, otio.schema.Transition):
            transition = self.aaf_transition(otio_child)
            return transition
        elif isinstance(otio_child, otio.schema.Clip):
            source_clip = self.aaf_sourceclip(otio_child)
            return source_clip
        elif isinstance(otio_child, otio.schema.Track):
            sequence = self.aaf_sequence(otio_child)
            return sequence
        elif isinstance(otio_child, otio.schema.Stack):
            operation_group = self.aaf_operation_group(otio_child)
            return operation_group
        else:
            raise otio.exceptions.NotSupportedError(
                f"Unsupported otio child type: {type(otio_child)}"
            )

    @property
    @abc.abstractmethod
    def media_kind(self):
        """Return the string for what kind of track this is."""
        pass

    @property
    @abc.abstractmethod
    def _master_mob_slot_id(self):
        """
        Return the MasterMob Slot ID for the corresponding track media kind
        """
        # MasterMob's and MasterMob slots have to be unique. We handle unique
        # MasterMob's with _unique_mastermob(). We also need to protect against
        # duplicate MasterMob slots. As of now, we mandate all picture clips to
        # be created in MasterMob slot 1 and all sound clips to be created in
        # MasterMob slot 2. While this is a little inadequate, it works for now
        pass

    @abc.abstractmethod
    def _create_timeline_mobslot(self):
        """
        Return a timeline_mobslot and sequence for this track.

        In AAF, a TimelineMobSlot is a container for the Sequence. A Sequence is
        analogous to an otio track.

        Returns:
            Returns a tuple of (TimelineMobSlot, Sequence)
        """
        pass

    @abc.abstractmethod
    def default_descriptor(self, otio_clip):
        pass

    @abc.abstractmethod
    def _transition_parameters(self):
        pass

    def aaf_network_locator(self, otio_external_ref):
        locator = self.aaf_file.create.NetworkLocator()
        locator["URLString"].value = otio_external_ref.target_url
        return locator

    def aaf_filler(self, otio_gap):
        """Convert an otio Gap into an aaf Filler"""
        import math
        # Convert duration from timeline rate to appropriate rate for media kind
        gap_duration = otio_gap.visible_range().duration
        if self.media_kind == "sound":
            # For Pro Tools compatibility: ceil frame count for Filler (upward)
            # This matches DaVinci Resolve's behavior where:
            # - Clip durations use floor (downward rounding)
            # - Gap/Filler durations use ceil (upward rounding)
            # This ensures total sequence length stays consistent
            frame_count = math.ceil(gap_duration.value)
            length = int(frame_count * (self.audio_sampling_rate / gap_duration.rate))
        else:
            length = int(gap_duration.value)
        filler = self.aaf_file.create.Filler(self.media_kind, length)
        return filler

    def aaf_sourceclip(self, otio_clip):
        """Convert an otio Clip into an aaf SourceClip"""
        tapemob, tapemob_slot = self._create_tapemob(otio_clip)
        filemob, filemob_slot = self._create_filemob(otio_clip, tapemob, tapemob_slot)
        mastermob, mastermob_slot = self._create_mastermob(
            otio_clip, filemob, filemob_slot
        )

        # We need both `start_time` and `duration`
        # Here `start` is the offset between `first` and `in` values.

        offset = (
            otio_clip.visible_range().start_time
            - otio_clip.available_range().start_time
        )
        start = offset.value
        length = otio_clip.visible_range().duration.value

        compmob_clip = self.compositionmob.create_source_clip(
            slot_id=self.timeline_mobslot.slot_id,
            # XXX: Python3 requires these to be passed as explicit ints
            start=int(start),
            length=int(length),
            media_kind=self.media_kind,
        )
        compmob_clip.mob = mastermob
        compmob_clip.slot = mastermob_slot
        compmob_clip.slot_id = mastermob_slot.slot_id
        return compmob_clip

    def aaf_transition(self, otio_transition):
        """Convert an otio Transition into an aaf Transition"""
        if (
            otio_transition.transition_type
            != otio.schema.TransitionTypes.SMPTE_Dissolve
        ):
            print(
                "Unsupported transition type: {}".format(
                    otio_transition.transition_type
                )
            )
            return None

        transition_params, varying_value = self._transition_parameters()

        interpolation_def = self.aaf_file.create.InterpolationDef(
            aaf2.misc.LinearInterp, "LinearInterp", "Linear keyframe interpolation"
        )
        self.aaf_file.dictionary.register_def(interpolation_def)
        varying_value["Interpolation"].value = (
            self.aaf_file.dictionary.lookup_interperlationdef("LinearInterp")
        )

        pointlist = otio_transition.metadata["AAF"]["PointList"]

        c1 = self.aaf_file.create.ControlPoint()
        c1["EditHint"].value = "Proportional"
        c1.value = pointlist[0]["Value"]
        c1.time = pointlist[0]["Time"]

        c2 = self.aaf_file.create.ControlPoint()
        c2["EditHint"].value = "Proportional"
        c2.value = pointlist[1]["Value"]
        c2.time = pointlist[1]["Time"]

        varying_value["PointList"].extend([c1, c2])

        op_group_metadata = otio_transition.metadata["AAF"]["OperationGroup"]
        effect_id = op_group_metadata["Operation"].get("Identification")
        is_time_warp = op_group_metadata["Operation"].get("IsTimeWarp")
        by_pass = op_group_metadata["Operation"].get("Bypass")
        number_inputs = op_group_metadata["Operation"].get("NumberInputs")
        operation_category = op_group_metadata["Operation"].get("OperationCategory")
        data_def_name = op_group_metadata["Operation"]["DataDefinition"]["Name"]
        data_def = self.aaf_file.dictionary.lookup_datadef(str(data_def_name))
        description = op_group_metadata["Operation"]["Description"]
        op_def_name = otio_transition.metadata["AAF"]["OperationGroup"]["Operation"][
            "Name"
        ]

        # Create OperationDefinition
        op_def = self.aaf_file.create.OperationDef(uuid.UUID(effect_id), op_def_name)
        self.aaf_file.dictionary.register_def(op_def)
        op_def.media_kind = self.media_kind
        datadef = self.aaf_file.dictionary.lookup_datadef(self.media_kind)
        op_def["IsTimeWarp"].value = is_time_warp
        op_def["Bypass"].value = by_pass
        op_def["NumberInputs"].value = number_inputs
        op_def["OperationCategory"].value = str(operation_category)
        op_def["ParametersDefined"].extend(transition_params)
        op_def["DataDefinition"].value = data_def
        op_def["Description"].value = str(description)

        # Create OperationGroup
        length = int(otio_transition.duration().value)
        operation_group = self.aaf_file.create.OperationGroup(op_def, length)
        operation_group["DataDefinition"].value = datadef
        operation_group["Parameters"].append(varying_value)

        # Create Transition
        transition = self.aaf_file.create.Transition(self.media_kind, length)
        transition["OperationGroup"].value = operation_group
        transition["CutPoint"].value = otio_transition.metadata["AAF"]["CutPoint"]
        transition["DataDefinition"].value = datadef
        return transition

    def aaf_sequence(self, otio_track):
        """Convert an otio Track into an aaf Sequence"""
        sequence = self.aaf_file.create.Sequence(media_kind=self.media_kind)
        sequence.components.value = []
        length = 0
        for nested_otio_child in otio_track:
            result = self.transcribe(nested_otio_child)
            length += result.length
            sequence.components.append(result)
        sequence.length = length
        return sequence

    def aaf_operation_group(self, otio_stack):
        """
        Create and return an OperationGroup which will contain other AAF objects
        to support OTIO nesting
        """
        # Create OperationDefinition
        op_def = self.aaf_file.create.OperationDef(
            AAF_OPERATIONDEF_SUBMASTER, "Submaster"
        )
        self.aaf_file.dictionary.register_def(op_def)
        op_def.media_kind = self.media_kind
        datadef = self.aaf_file.dictionary.lookup_datadef(self.media_kind)

        # These values are necessary for pyaaf2 OperationDefinitions
        op_def["IsTimeWarp"].value = False
        op_def["Bypass"].value = 0
        op_def["NumberInputs"].value = -1
        op_def["OperationCategory"].value = "OperationCategory_Effect"
        op_def["DataDefinition"].value = datadef

        # Create OperationGroup
        operation_group = self.aaf_file.create.OperationGroup(op_def)
        operation_group.media_kind = self.media_kind
        operation_group["DataDefinition"].value = datadef

        length = 0
        for nested_otio_child in otio_stack:
            result = self.transcribe(nested_otio_child)
            length += result.length
            operation_group.segments.append(result)
        operation_group.length = length
        return operation_group

    def _create_tapemob(self, otio_clip):
        """
        Return a physical sourcemob for an otio Clip based on the MobID.

        Returns:
            Returns a tuple of (TapeMob, TapeMobSlot)
        """
        tapemob = self.root_file_transcriber._unique_tapemob(otio_clip)

        # For audio tracks, use audio sampling rate as edit rate
        slot_edit_rate = self.edit_rate
        if self.media_kind == "sound":
            slot_edit_rate = getattr(self, 'audio_sampling_rate', 48000)

        tapemob_slot = tapemob.create_empty_slot(slot_edit_rate, self.media_kind)
        tapemob_slot["PhysicalTrackNumber"].value = 1

        # Calculate length in appropriate units
        if self.media_kind == "sound":
            # Audio: length in samples
            available_range = otio_clip.media_reference.available_range
            duration_seconds = (
                available_range.duration.value / available_range.duration.rate
            )
            tapemob_slot.segment.length = int(
                duration_seconds * self.audio_sampling_rate
            )
        else:
            # Video: length in frames
            tapemob_slot.segment.length = int(
                otio_clip.media_reference.available_range.duration.value
            )
        return tapemob, tapemob_slot

    def _create_filemob(self, otio_clip, tapemob, tapemob_slot):
        """
        Return a file sourcemob with WAVEDescriptor for an otio Clip.
        This is the SourceMob that contains the actual media reference.

        Returns:
            Returns a tuple of (FileMob, FileMobSlot)
        """
        mob_id = self.root_file_transcriber._clip_mob_ids_map.get(otio_clip)
        filemob = self.root_file_transcriber._filemobs.get(mob_id)

        if not filemob:
            filemob = self.aaf_file.create.SourceMob()
            filemob.name = otio_clip.name  # WAVEDescriptor SourceMob has the clip name
            filemob.descriptor = self.default_descriptor(otio_clip)
            _patch_mob_id_prefix(filemob)
            self.root_file_transcriber._filemobs[mob_id] = filemob

        # For audio tracks, use audio sampling rate as edit rate
        slot_edit_rate = self.edit_rate
        if self.media_kind == "sound":
            slot_edit_rate = getattr(self, 'audio_sampling_rate', 48000)

        filemob_slot = filemob.create_timeline_slot(slot_edit_rate)
        filemob_slot["PhysicalTrackNumber"].value = 1
        filemob_clip = filemob.create_source_clip(
            slot_id=filemob_slot.slot_id,
            length=tapemob_slot.segment.length,  # Use the calculated length
            media_kind=tapemob_slot.segment.media_kind,
        )
        filemob_clip.mob = tapemob
        filemob_clip.slot = tapemob_slot
        filemob_clip.slot_id = tapemob_slot.slot_id
        filemob_slot.segment = filemob_clip
        return filemob, filemob_slot

    def _create_mastermob(self, otio_clip, filemob, filemob_slot):
        """
        Return a mastermob for an otio Clip. Needs a filemob and filemob slot.

        Returns:
            Returns a tuple of (MasterMob, MasterMobSlot)
        """
        mastermob = self.root_file_transcriber._unique_mastermob(otio_clip)

        # Calculate length in appropriate units
        if self.media_kind == "sound":
            # Audio: length in samples
            available_range = otio_clip.media_reference.available_range
            duration_seconds = (
                available_range.duration.value / available_range.duration.rate
            )
            timecode_length = int(duration_seconds * self.audio_sampling_rate)
        else:
            # Video: length in frames
            timecode_length = int(
                otio_clip.media_reference.available_range.duration.value
            )

        try:
            mastermob_slot = mastermob.slot_at(self._master_mob_slot_id)
        except IndexError:
            # For audio tracks, use audio sampling rate as edit rate
            slot_edit_rate = self.edit_rate
            if self.media_kind == "sound":
                slot_edit_rate = getattr(self, 'audio_sampling_rate', 48000)

            mastermob_slot = mastermob.create_timeline_slot(
                edit_rate=slot_edit_rate, slot_id=self._master_mob_slot_id
            )
        mastermob_slot["PhysicalTrackNumber"].value = 1
        mastermob_clip = mastermob.create_source_clip(
            slot_id=mastermob_slot.slot_id,
            length=timecode_length,
            media_kind=self.media_kind,
        )
        mastermob_clip.mob = filemob
        mastermob_clip.slot = filemob_slot
        mastermob_clip.slot_id = filemob_slot.slot_id
        mastermob_slot.segment = mastermob_clip
        return mastermob, mastermob_slot


class VideoTrackTranscriber(_TrackTranscriber):
    """Video track kind specialization of TrackTranscriber."""

    @property
    def media_kind(self):
        return "picture"

    @property
    def _master_mob_slot_id(self):
        return 2  # Use slot ID 2 for video (audio uses 1)

    def _create_timeline_mobslot(self):
        """
        Create a Sequence container (TimelineMobSlot) and Sequence.

        TimelineMobSlot --> Sequence
        """
        # SlotID 1 is reserved for timecode, so video tracks start from SlotID 2
        # Find the next available slot ID
        existing_slot_ids = set(slot.slot_id for slot in self.compositionmob.slots)
        slot_id = 2
        while slot_id in existing_slot_ids:
            slot_id += 1

        timeline_mobslot = self.compositionmob.create_timeline_slot(
            edit_rate=self.edit_rate
        )
        timeline_mobslot.slot_id = slot_id
        sequence = self.aaf_file.create.Sequence(media_kind=self.media_kind)
        sequence.components.value = []
        timeline_mobslot.segment = sequence
        return timeline_mobslot, sequence

    def default_descriptor(self, otio_clip):
        # TODO: Determine if these values are the correct, and if so,
        # maybe they should be in the AAF metadata
        descriptor = self.aaf_file.create.CDCIDescriptor()
        descriptor["ComponentWidth"].value = 8
        descriptor["HorizontalSubsampling"].value = 2
        descriptor["ImageAspectRatio"].value = "16/9"
        descriptor["StoredWidth"].value = 1920
        descriptor["StoredHeight"].value = 1080
        descriptor["FrameLayout"].value = "FullFrame"
        descriptor["VideoLineMap"].value = [42, 0]
        descriptor["SampleRate"].value = 24
        descriptor["Length"].value = 1

        media = otio_clip.media_reference
        if isinstance(media, otio.schema.ExternalReference):
            if media.target_url:
                locator = self.aaf_network_locator(media)
                descriptor["Locator"].append(locator)
            if media.available_range:
                descriptor["SampleRate"].value = media.available_range.duration.rate
                descriptor["Length"].value = int(media.available_range.duration.value)

        return descriptor

    def _transition_parameters(self):
        """
        Return video transition parameters
        """
        # Create ParameterDef for AvidParameterByteOrder
        byteorder_typedef = self.aaf_file.dictionary.lookup_typedef("aafUInt16")
        param_byteorder = self.aaf_file.create.ParameterDef(
            AAF_PARAMETERDEF_AVIDPARAMETERBYTEORDER,
            "AvidParameterByteOrder",
            "",
            byteorder_typedef,
        )
        self.aaf_file.dictionary.register_def(param_byteorder)

        # Create ParameterDef for AvidEffectID
        avid_effect_typdef = self.aaf_file.dictionary.lookup_typedef("AvidBagOfBits")
        param_effect_id = self.aaf_file.create.ParameterDef(
            AAF_PARAMETERDEF_AVIDEFFECTID, "AvidEffectID", "", avid_effect_typdef
        )
        self.aaf_file.dictionary.register_def(param_effect_id)

        # Create ParameterDef for AFX_FG_KEY_OPACITY_U
        opacity_param_def = self.aaf_file.dictionary.lookup_typedef("Rational")
        opacity_param = self.aaf_file.create.ParameterDef(
            AAF_PARAMETERDEF_AFX_FG_KEY_OPACITY_U,
            "AFX_FG_KEY_OPACITY_U",
            "",
            opacity_param_def,
        )
        self.aaf_file.dictionary.register_def(opacity_param)

        # Create VaryingValue
        opacity_u = self.aaf_file.create.VaryingValue()
        opacity_u.parameterdef = self.aaf_file.dictionary.lookup_parameterdef(
            "AFX_FG_KEY_OPACITY_U"
        )
        opacity_u["VVal_Extrapolation"].value = AAF_VVAL_EXTRAPOLATION_ID
        opacity_u["VVal_FieldCount"].value = 1

        return [param_byteorder, param_effect_id], opacity_u


class AudioTrackTranscriber(_TrackTranscriber):
    """Audio track kind specialization of TrackTranscriber."""

    @property
    def media_kind(self):
        return "sound"

    @property
    def _master_mob_slot_id(self):
        return 1  # Use slot ID 1 for audio, matching DaVinci Resolve output

    @property
    def audio_sampling_rate(self):
        """Get the audio sampling rate from the first audio clip's WAV file."""
        self._ensure_wav_info()
        return self._cached_sample_rate

    @property
    def audio_bits_per_sample(self):
        """Get the audio bit depth from the first audio clip's WAV file."""
        self._ensure_wav_info()
        return self._cached_bits_per_sample

    def _ensure_wav_info(self):
        """Read sample rate and bit depth from the first available WAV file."""
        if hasattr(self, '_cached_sample_rate'):
            return

        import struct
        import os
        for child in self.otio_track:
            if not hasattr(child, 'media_reference') or not child.media_reference:
                continue
            mr = child.media_reference
            if not hasattr(mr, 'target_url') or not mr.target_url:
                continue

            # Handle various path formats (same as _build_wav_summary)
            wav_path = mr.target_url
            if wav_path.startswith("file:///"):
                wav_path = wav_path[8:]
                # Handle Windows paths: file:///C:/... -> C:\...
                if len(wav_path) >= 2 and wav_path[1] == ':':
                    wav_path = wav_path.replace("/", os.sep)
            elif wav_path.startswith("file://"):
                wav_path = wav_path[7:]
                if len(wav_path) >= 2 and wav_path[1] == ':':
                    wav_path = wav_path.replace("/", os.sep)

            # Handle Windows extended-length path prefix \\?\
            if wav_path.startswith("\\\\?\\"):
                wav_path = wav_path[4:]

            try:
                with open(wav_path, 'rb') as wf:
                    header = wf.read(4096)
                if (
                    len(header) >= 44
                    and header[0:4] == b'RIFF'
                    and header[8:12] == b'WAVE'
                ):
                    pos = 12
                    while pos + 8 <= len(header):
                        chunk_id = header[pos:pos + 4]
                        chunk_size = struct.unpack_from('<I', header, pos + 4)[0]
                        if chunk_id == b'fmt ':
                            self._cached_sample_rate = (
                                struct.unpack_from('<I', header, pos + 12)[0]
                            )
                            self._cached_bits_per_sample = (
                                struct.unpack_from('<H', header, pos + 22)[0]
                            )
                            return
                        pos += 8 + chunk_size
            except (OSError, FileNotFoundError):
                continue

        self._cached_sample_rate = 48000
        self._cached_bits_per_sample = 16

    def _create_timeline_mobslot(self):
        """
        Create a Sequence container (TimelineMobSlot) and Sequence.
        For Pro Tools compatibility, we use a simple Sequence, not an OperationGroup.

        TimelineMobSlot --> Sequence
        """
        # Use audio sampling rate as edit rate for audio tracks
        audio_edit_rate = self.audio_sampling_rate

        # TimelineMobSlot
        # SlotID 1 = timecode, SlotID 2 = reserved for video.
        # Audio tracks start from SlotID 3 (matching DaVinci Resolve layout).
        existing_slot_ids = set(slot.slot_id for slot in self.compositionmob.slots)
        slot_id = 3
        while slot_id in existing_slot_ids:
            slot_id += 1

        timeline_mobslot = self.compositionmob.create_sound_slot(
            edit_rate=audio_edit_rate
        )
        timeline_mobslot.slot_id = slot_id
        timeline_mobslot.name = self.otio_track.name

        # Set PhysicalTrackNumber for audio tracks (important for Pro Tools)
        # Audio tracks should have PhysicalTrackNumber starting from 1
        timeline_mobslot["PhysicalTrackNumber"].value = 1

        # Sequence (not wrapped in OperationGroup)
        sequence = self.aaf_file.create.Sequence(media_kind=self.media_kind)
        sequence.components.value = []
        sequence.length = 0  # Will be calculated during transcription
        timeline_mobslot.segment = sequence
        return timeline_mobslot, sequence

    def aaf_sourceclip(self, otio_clip):
        """
        Create a source clip for audio with proper edit rate handling.
        Audio clips use the audio sampling rate (48000) as edit rate,
        while the composition uses the timeline rate (24 fps).

        For Pro Tools compatibility, each audio clip is wrapped in an
        Audio Gain OperationGroup (matching DaVinci Resolve's output structure).
        """
        # Track which mobs are new (not yet in unique dicts)
        mob_id = self.root_file_transcriber._clip_mob_ids_map.get(otio_clip)
        mastermob_is_new = mob_id not in self.root_file_transcriber._unique_mastermobs
        tapemob_is_new = mob_id not in self.root_file_transcriber._unique_tapemobs
        filemob_is_new = mob_id not in self.root_file_transcriber._filemobs

        tapemob, tapemob_slot = self._create_tapemob(otio_clip)
        filemob, filemob_slot = self._create_filemob(otio_clip, tapemob, tapemob_slot)
        mastermob, mastermob_slot = self._create_mastermob(
            otio_clip, filemob, filemob_slot
        )

        # Append mobs in correct order: MasterMob, TapeMob, FileMob
        # This matches DaVinci Resolve's output order
        if mastermob_is_new:
            self.root_file_transcriber._mobs_to_append.append(('master', mastermob))
        if tapemob_is_new:
            self.root_file_transcriber._mobs_to_append.append(('tape', tapemob))
        if filemob_is_new:
            self.root_file_transcriber._mobs_to_append.append(('file', filemob))

        # Convert duration from timeline rate (24 fps) to audio sampling rate (48000 Hz)
        # For Pro Tools compatibility: round frame count first, then convert to samples
        # This matches DaVinci Resolve's behavior (clean integer sample counts)
        visible_duration = otio_clip.visible_range().duration
        if self.media_kind == "sound":
            # Use floor (int) for frame count - matches DaVinci Resolve's behavior
            frame_count = int(visible_duration.value)
            length = int(
                frame_count * (self.audio_sampling_rate / visible_duration.rate)
            )
        else:
            length = int(visible_duration.value)

        # When the SourceClip is wrapped in an OperationGroup, the OperationGroup
        # handles timeline positioning. The inner SourceClip should start at 0
        # (reference from the beginning of the MasterMob).
        # This matches DaVinci Resolve's behavior: StartTime=0 for OG input clips.
        compmob_clip = self.compositionmob.create_source_clip(
            slot_id=self.timeline_mobslot.slot_id,
            start=0,
            length=int(length),
            media_kind=self.media_kind,
        )
        compmob_clip.mob = mastermob
        compmob_clip.slot = mastermob_slot
        compmob_clip.slot_id = mastermob_slot.slot_id

        # Wrap the SourceClip in an Audio Gain OperationGroup
        # This matches DaVinci Resolve's output structure for Pro Tools compatibility
        op_group = self._create_audio_gain_opgroup(compmob_clip, length)
        return op_group

    def default_descriptor(self, otio_clip):
        """
        Create a WAVEDescriptor for audio files.
        This matches DaVinci Resolve's output format.
        """
        # Get audio info from media reference
        media = otio_clip.media_reference
        available_range = media.available_range if media else None

        # Calculate length in audio samples
        if available_range:
            # Duration in seconds * sample rate = samples
            duration_seconds = (
                available_range.duration.value / available_range.duration.rate
            )
            length_samples = int(duration_seconds * self.audio_sampling_rate)
        else:
            length_samples = 438000  # Default fallback

        # Use WAVEDescriptor for compatibility with DaVinci Resolve
        descriptor = self.aaf_file.create.WAVEDescriptor()
        descriptor["SampleRate"].value = self.audio_sampling_rate
        descriptor["Length"].value = length_samples

        # Add locator for external reference
        if isinstance(media, otio.schema.ExternalReference) and media.target_url:
            locator = self.aaf_network_locator(media)

            # Build proper file:// URL using Path.as_uri()
            from pathlib import Path

            target_url = media.target_url

            # Strip file:// prefix if already present
            if target_url.startswith("file:///"):
                target_url = target_url[8:]
            elif target_url.startswith("file://"):
                target_url = target_url[7:]

            # Strip Windows extended-length prefix \\?\
            if target_url.startswith("\\\\?\\"):
                target_url = target_url[4:]

            # Path.as_uri() handles everything: file:// prefix,
            # URL encoding, path normalization
            url_string = Path(target_url).resolve().as_uri()

            locator["URLString"].value = url_string
            descriptor["Locator"].append(locator)

        # Add Summary (WAV header bytes) — read from actual WAV file
        # WAVEDescriptor requires Summary property, so always provide one
        summary = self._build_wav_summary(media, length_samples)
        if summary:
            descriptor["Summary"].value = summary
        else:
            # Provide default Summary if WAV file can't be read
            descriptor["Summary"].value = (
                self._build_default_wav_summary(length_samples)
            )

        return descriptor

    def _build_wav_summary(self, media, length_samples):
        """Read actual WAV file and build a standardized 44-byte Summary header."""
        import struct
        if not isinstance(media, otio.schema.ExternalReference) or not media.target_url:
            return None

        # Handle various path formats
        wav_path = media.target_url
        if wav_path.startswith("file:///"):
            wav_path = wav_path[8:]
            # Handle Windows paths: file:///C:/... -> C:\...
            if len(wav_path) >= 2 and wav_path[1] == ':':
                wav_path = wav_path.replace("/", os.sep)
        elif wav_path.startswith("file://"):
            wav_path = wav_path[7:]
            if len(wav_path) >= 2 and wav_path[1] == ':':
                wav_path = wav_path.replace("/", os.sep)

        # Handle Windows extended-length path prefix \\?\
        if wav_path.startswith("\\\\?\\"):
            wav_path = wav_path[4:]

        try:
            with open(wav_path, 'rb') as f:
                raw = f.read(4096)
        except (OSError, FileNotFoundError) as e:
            print(f"Warning: Could not read WAV file {wav_path}: {e}")
            return None

        if len(raw) < 44 or raw[0:4] != b'RIFF' or raw[8:12] != b'WAVE':
            return None

        riff_size = struct.unpack_from('<I', raw, 4)[0]

        # Walk chunks to find fmt and data
        pos = 12
        channels = 1
        sample_rate = self.audio_sampling_rate
        byte_rate = sample_rate
        block_align = 2
        bits_per_sample = 16
        data_size = 0

        while pos + 8 <= len(raw):
            chunk_id = raw[pos:pos + 4]
            chunk_size = struct.unpack_from('<I', raw, pos + 4)[0]
            if chunk_id == b'fmt ':
                channels = struct.unpack_from('<H', raw, pos + 10)[0]
                sample_rate = struct.unpack_from('<I', raw, pos + 12)[0]
                byte_rate = struct.unpack_from('<I', raw, pos + 16)[0]
                block_align = struct.unpack_from('<H', raw, pos + 20)[0]
                bits_per_sample = struct.unpack_from('<H', raw, pos + 22)[0]
            elif chunk_id == b'data':
                data_size = chunk_size
            pos += 8 + chunk_size

        # Standardize: write PCM format (1) with fmt chunk size 16
        summary = bytearray(44)
        struct.pack_into('<4s', summary, 0, b'RIFF')
        struct.pack_into('<I', summary, 4, riff_size)
        struct.pack_into('<4s', summary, 8, b'WAVE')
        struct.pack_into('<4s', summary, 12, b'fmt ')
        struct.pack_into('<I', summary, 16, 16)
        struct.pack_into('<H', summary, 20, 1)  # PCM
        struct.pack_into('<H', summary, 22, channels)
        struct.pack_into('<I', summary, 24, sample_rate)
        struct.pack_into('<I', summary, 28, byte_rate)
        struct.pack_into('<H', summary, 32, block_align)
        struct.pack_into('<H', summary, 34, bits_per_sample)
        struct.pack_into('<4s', summary, 36, b'data')
        struct.pack_into('<I', summary, 40, data_size)

        return summary

    def _build_default_wav_summary(self, length_samples):
        """Build a default WAV Summary header when actual WAV file is unavailable."""
        import struct
        channels = 1
        sample_rate = self.audio_sampling_rate
        bits_per_sample = 16
        byte_rate = sample_rate * channels * bits_per_sample // 8
        block_align = channels * bits_per_sample // 8
        data_size = length_samples * block_align
        riff_size = 36 + data_size

        summary = bytearray(44)
        struct.pack_into('<4s', summary, 0, b'RIFF')
        struct.pack_into('<I', summary, 4, riff_size)
        struct.pack_into('<4s', summary, 8, b'WAVE')
        struct.pack_into('<4s', summary, 12, b'fmt ')
        struct.pack_into('<I', summary, 16, 16)
        struct.pack_into('<H', summary, 20, 1)  # PCM
        struct.pack_into('<H', summary, 22, channels)
        struct.pack_into('<I', summary, 24, sample_rate)
        struct.pack_into('<I', summary, 28, byte_rate)
        struct.pack_into('<H', summary, 32, block_align)
        struct.pack_into('<H', summary, 34, bits_per_sample)
        struct.pack_into('<4s', summary, 36, b'data')
        struct.pack_into('<I', summary, 40, data_size)

        return summary

    def _transition_parameters(self):
        """
        Return audio transition parameters
        """
        # Create ParameterDef for ParameterDef_Level
        def_level_typedef = self.aaf_file.dictionary.lookup_typedef("Rational")
        param_def_level = self.aaf_file.create.ParameterDef(
            AAF_PARAMETERDEF_LEVEL, "ParameterDef_Level", "", def_level_typedef
        )
        self.aaf_file.dictionary.register_def(param_def_level)

        # Create VaryingValue
        level = self.aaf_file.create.VaryingValue()
        level.parameterdef = self.aaf_file.dictionary.lookup_parameterdef(
            "ParameterDef_Level"
        )

        return [param_def_level], level

    def _create_audio_gain_opgroup(self, source_clip, length):
        """
        Create an Audio Gain OperationGroup wrapping a SourceClip.
        This matches DaVinci Resolve's output structure for Pro Tools compatibility.

        Args:
            source_clip: The SourceClip to wrap
            length: The length in audio samples

        Returns:
            OperationGroup containing the SourceClip with a default Audio Gain effect
        """
        import aaf2.rational

        # Create or lookup the Audio Gain OperationDefinition
        op_def = self.aaf_file.create.OperationDef(
            AAF_OPERATIONDEF_AUDIOGAIN, "Audio Gain"
        )
        self.aaf_file.dictionary.register_def(op_def)
        op_def.media_kind = self.media_kind
        datadef = self.aaf_file.dictionary.lookup_datadef(self.media_kind)

        # Required properties for OperationDefinition
        op_def["IsTimeWarp"].value = False
        op_def["Bypass"].value = 0
        op_def["NumberInputs"].value = 1
        op_def["OperationCategory"].value = "OperationCategory_Effect"
        op_def["DataDefinition"].value = datadef

        # Create the Amplitude ParameterDef if not already registered
        # DaVinci Resolve uses "Amplitude" (not "ParameterDef_Level") for Audio Gain
        try:
            param_def_level = self.aaf_file.dictionary.lookup_parameterdef("Amplitude")
        except Exception:
            def_level_typedef = self.aaf_file.dictionary.lookup_typedef("Rational")
            param_def_level = self.aaf_file.create.ParameterDef(
                AAF_PARAMETERDEF_AMPLITUDE, "Amplitude", "", def_level_typedef
            )
            self.aaf_file.dictionary.register_def(param_def_level)

        # Create ConstantValue for the gain parameter
        # Value is 536870912/536870912 = 1.0 (no attenuation)
        # This matches DaVinci Resolve's default Audio Gain value
        const_value = self.aaf_file.create.ConstantValue()
        const_value.parameterdef = param_def_level
        const_value["Value"].value = aaf2.rational.AAFRational(536870912, 536870912)

        # Create the OperationGroup
        op_group = self.aaf_file.create.OperationGroup(op_def, length)
        op_group.media_kind = self.media_kind
        op_group["DataDefinition"].value = datadef

        # Add the SourceClip as input
        op_group.segments.append(source_clip)

        # Add the ConstantValue parameter
        op_group["Parameters"].append(const_value)

        return op_group


class __check:
    """
    __check is a private helper class that safely gets values given to check
    for existence and equality
    """

    def __init__(self, obj, tokenpath):
        self.orig = obj
        self.value = obj
        self.errors = []
        self.tokenpath = tokenpath
        try:
            for token in re.split(r"[\.\[]", tokenpath):
                if token.endswith("()"):
                    self.value = getattr(self.value, token.replace("()", ""))()
                elif "]" in token:
                    self.value = self.value[token.strip("[]'\"")]
                else:
                    self.value = getattr(self.value, token)
        except Exception as e:
            self.value = None
            self.errors.append(
                "{}{} {}.{} does not exist, {}".format(
                    self.orig.name if hasattr(self.orig, "name") else "",
                    type(self.orig),
                    type(self.orig).__name__,
                    self.tokenpath,
                    e,
                )
            )

    def equals(self, val):
        """Check if the retrieved value is equal to a given value."""
        if self.value is not None and self.value != val:
            self.errors.append(
                "{}{} {}.{} not equal to {} (expected) != {} (actual)".format(
                    self.orig.name if hasattr(self.orig, "name") else "",
                    type(self.orig),
                    type(self.orig).__name__,
                    self.tokenpath,
                    val,
                    self.value,
                )
            )
        return self
